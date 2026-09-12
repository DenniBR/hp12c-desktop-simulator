"""TVM, amortization, simple interest, NPV/IRR, depreciation, bonds.

Formulas are transcribed from Appendix D ("Formulas Used") of the hp-12c
user's guide. The odd-period TVM variants (simple/compound interest for a
fractional first period) are NOT implemented -- the manual does not state
which the plain n/i/PV/PMT/FV keys use by default, so guessing would be
"invented precision". Only the no-odd-period case (the documented default
path) is implemented and tested; see docs/COMPATIBILITY.md.
"""
import decimal
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from math import log

from .decimal_ctx import round10
from .errors import Error3IRR, Error5CompoundInterest, Error7IRR

D = Decimal


def _pow(base: Decimal, exp: Decimal) -> Decimal:
    """base**exp for Decimal, robust to huge exponents (unlike float**float,
    which overflows around 1e308 -- Decimal.exp()/ln() do not)."""
    if base == 0:
        return D(0) if exp > 0 else D(1)
    if base < 0:
        int_exp = exp.to_integral_value()
        if exp != int_exp:
            raise InvalidOperation("negative base with fractional exponent")
        return base ** int(int_exp)
    return (exp * base.ln()).exp()


def fv_factor(i: Decimal, n: Decimal) -> Decimal:
    """(1+i)^n, works for non-integer n (odd-period-free path)."""
    return _pow(D(1) + i, n)


def annuity_factor(i: Decimal, n: Decimal, fvif: Decimal) -> Decimal:
    """[(1+i)^n - 1] / i, with the i->0 limit (= n) handled explicitly."""
    if i == 0:
        return n
    return (fvif - D(1)) / i


def solve_pv(n: Decimal, i: Decimal, pmt: Decimal, fv: Decimal, begin: bool) -> Decimal:
    s = D(1) if begin else D(0)
    fvif = fv_factor(i, n)
    af = annuity_factor(i, n, fvif)
    pmt_term = pmt * (D(1) + i * s) * af
    if fvif == 0:
        raise Error5CompoundInterest()
    return round10(-(fv + pmt_term) / fvif)


def solve_fv(n: Decimal, i: Decimal, pv: Decimal, pmt: Decimal, begin: bool) -> Decimal:
    s = D(1) if begin else D(0)
    fvif = fv_factor(i, n)
    af = annuity_factor(i, n, fvif)
    pmt_term = pmt * (D(1) + i * s) * af
    return round10(-(pv * fvif + pmt_term))


def solve_pmt(n: Decimal, i: Decimal, pv: Decimal, fv: Decimal, begin: bool) -> Decimal:
    s = D(1) if begin else D(0)
    fvif = fv_factor(i, n)
    af = annuity_factor(i, n, fvif)
    denom = (D(1) + i * s) * af
    if denom == 0:
        raise Error5CompoundInterest()
    return round10(-(pv * fvif + fv) / denom)


def solve_n(i: Decimal, pv: Decimal, pmt: Decimal, fv: Decimal, begin: bool) -> Decimal:
    s = D(1) if begin else D(0)
    if i == 0:
        if pmt == 0:
            raise Error5CompoundInterest()
        n = -(fv + pv) / pmt
    else:
        k = pmt * (D(1) + i * s) / i
        numerator = k - fv
        denominator = pv + k
        if denominator == 0 or numerator / denominator <= 0:
            raise Error5CompoundInterest()
        n = D(log(float(numerator / denominator)) / log(float(D(1) + i)))
    # "n is rounded up by the calculator to show the total number of payments
    # needed" (p.40-41).
    import math
    n_int = D(math.ceil(round10(n)))
    return n_int


def solve_i(n: Decimal, pv: Decimal, pmt: Decimal, fv: Decimal, begin: bool) -> Decimal:
    """No closed form; the manual does not publish the firmware's iteration
    algorithm, so this uses bisection (documented in COMPATIBILITY.md as not
    bit-exact to firmware, but numerically convergent to the same 10
    significant digits for well-posed problems)."""
    s = D(1) if begin else D(0)

    def f(i: Decimal) -> Decimal:
        if i == 0:
            return pv + pmt * n + fv
        fvif = fv_factor(i, n)
        af = annuity_factor(i, n, fvif)
        return pv * fvif + pmt * (D(1) + i * s) * af + fv

    lo, hi = D("-0.999999"), D(10)
    try:
        flo, fhi = f(lo), f(hi)
    except (OverflowError, decimal.DecimalException):
        raise Error5CompoundInterest()
    if flo == 0:
        return round10(lo)
    if fhi == 0:
        return round10(hi)
    if (flo > 0) == (fhi > 0):
        # widen search for a sign change up to a generous bound
        found = False
        hi = D(10)
        for _ in range(60):
            hi = hi * 2
            try:
                fhi = f(hi)
            except (OverflowError, decimal.DecimalException):
                break
            if (flo > 0) != (fhi > 0):
                found = True
                break
        if not found:
            raise Error5CompoundInterest()

    for _ in range(200):
        mid = (lo + hi) / 2
        try:
            fmid = f(mid)
        except (OverflowError, decimal.DecimalException):
            raise Error5CompoundInterest()
        if fmid == 0 or (hi - lo) < D("1E-13"):
            return round10(mid)
        if (fmid > 0) == (flo > 0):
            lo, flo = mid, fmid
        else:
            hi = mid
    return round10((lo + hi) / 2)


# ---------------------------------------------------------------- amort ----
def amortize(count: int, pv: Decimal, pmt: Decimal, i: Decimal, begin: bool, period: int,
             display_places: int = 2):
    """Amortize `count` periods starting at absolute period `period`
    (1-based). Returns (interest, principal, new_pv). Matches Appendix D's
    per-period recursion exactly (not a closed-form aggregate).

    Appendix D marks each period's interest with an explicit RND subscript
    ("INTj = |PVj-1 x i|RND x sign(PMT)"): it is rounded to the CURRENT
    DISPLAY decimal places (not the usual 10-significant-digit register
    width) before being used in the next period -- confirmed by matching the
    manual's own worked example (p.54-55: 25yr/13.25%/$50,000/$-573.35 =>
    first-year interest -6,608.89) bit for bit; using round10 instead gives
    -6,608.917077, which does not match the manual's real output.
    """
    quantum = Decimal(1).scaleb(-display_places)
    running_pv = pv
    total_int = D(0)
    total_prn = D(0)
    sign = D(1) if pmt >= 0 else D(-1)
    for j in range(period, period + count):
        if j == 1 and begin:
            interest = D(0)
        else:
            interest = abs(running_pv * i).quantize(quantum, rounding=ROUND_HALF_UP) * sign
        prn = pmt - interest
        running_pv = round10(running_pv + prn)
        total_int += interest
        total_prn += prn
    return round10(total_int), round10(total_prn), running_pv


# --------------------------------------------------------- simple interest -
def simple_interest(n: Decimal, pv: Decimal, i: Decimal):
    """Returns (interest_360, interest_365). n is a NUMBER OF DAYS (per p.33:
    "Key in or calculate the number of days, then press n") and i is the
    ANNUAL decimal rate -- not periodic. Uses -PV, matching the Appendix A
    stack table (Y becomes "-PV") and the p.33-34 worked example: PV is
    stored negative (-450, cash-flow-sign convention) via CHS PV, but the
    displayed interest is positive (+5.25); n*pv*i/360 alone would be
    negative, so -pv is used. Validated bit-for-bit against that example
    (n=60, PV=-450, i=0.07 => 5.25 / 5.18)."""
    i360 = round10(n * -pv * i / D(360))
    i365 = round10(n * -pv * i / D(365))
    return i360, i365


# -------------------------------------------------------------- NPV / IRR --
def npv(rate: Decimal, cashflows: list, counts: list) -> Decimal:
    total = D(0)
    period = 0
    for cf, cnt in zip(cashflows, counts):
        for _ in range(cnt):
            total += cf / fv_factor(rate, D(period))
            period += 1
    return round10(total)


def irr(cashflows: list, counts: list) -> Decimal:
    flat = []
    for cf, cnt in zip(cashflows, counts):
        flat.extend([cf] * cnt)
    if not flat:
        raise Error7IRR()
    signs = {1 if c > 0 else (-1 if c < 0 else 0) for c in flat}
    if len(signs - {0}) < 2:
        raise Error7IRR()

    def f(rate: Decimal) -> Decimal:
        return npv(rate, cashflows, counts)

    lo, hi = D("-0.999999"), D(1)
    flo = f(lo)
    fhi = f(hi)
    tries = 0
    while (flo > 0) == (fhi > 0) and tries < 60:
        hi *= 2
        fhi = f(hi)
        tries += 1
    if (flo > 0) == (fhi > 0):
        raise Error3IRR()
    for _ in range(200):
        mid = (lo + hi) / 2
        fmid = f(mid)
        if fmid == 0 or (hi - lo) < D("1E-12"):
            return round10(mid * 100)  # IRR displayed as a percentage
        if (fmid > 0) == (flo > 0):
            lo, flo = mid, fmid
        else:
            hi = mid
    raise Error3IRR()


# ------------------------------------------------------------ depreciation -
# Inputs per the manual's own instructions (p.68): cost via PV, salvage via
# FV, useful life via n, declining-balance factor (%) via i; only the year
# number is keyed directly into X. Output register layout (Appendix A,
# p.175): X=DPN (depreciation), Y=RDV/RBV (remaining value) -- not just DPN
# alone, which is what an earlier version of this module returned.
def depreciation_sl(sbv: Decimal, sal: Decimal, life: Decimal, period: Decimal):
    dpn = round10((sbv - sal) / life)
    rdv = round10((sbv - sal) - dpn * period)
    return dpn, rdv


def depreciation_soyd(sbv: Decimal, sal: Decimal, life: Decimal, period: Decimal):
    lw = int(life)
    soyd_sum = D(lw * (lw + 1) / 2)
    dpn = round10((D(lw) - period + D(1)) / soyd_sum * (sbv - sal))
    # RDVj = (SBV-SAL) - sum_{k=1..j} DPNk; closed form of that sum:
    depreciable = sbv - sal
    sum_dpn = depreciable / soyd_sum * (period * D(lw) - period * (period - 1) / 2)
    rdv = round10(depreciable - sum_dpn)
    return dpn, rdv


def depreciation_db(rbv_prev: Decimal, fact: Decimal, life: Decimal):
    """rbv_prev is the remaining BOOK value from the previous year (RBV0 =
    SBV.) The engine persists this across calls the same way it persists PV
    across AMORT calls -- see docs/COMPATIBILITY.md."""
    dpn = round10(rbv_prev * fact / D(100) / life)
    rbv = round10(rbv_prev - dpn)
    return dpn, rbv


# ------------------------------------------------------------------ bonds --
def bond_price(settlement, maturity, coupon_pct: Decimal, yield_pct: Decimal,
                redemption: Decimal = D(100)):
    """Semiannual-coupon bond clean price, per Appendix D / the manual's
    cited source (Spence, Graudenz & Lynch, Standard Securities Calculation
    Methods). Actual/actual day counts (30/360 bonds are NOT covered -- see
    docs/COMPATIBILITY.md). Returns (clean_price, accrued_interest)."""
    from . import calendar_fns as cal

    coupon_dates = [maturity]
    d = maturity
    while d > settlement:
        d = cal.add_months(d, -6)
        coupon_dates.append(d)
    period_start = coupon_dates[-1]
    period_end = coupon_dates[-2] if len(coupon_dates) >= 2 else maturity
    e_days = (period_end - period_start).days
    dcs = (settlement - period_start).days
    dsc = e_days - dcs
    dsm = (maturity - settlement).days
    n_coupons = len(coupon_dates) - 1

    cpn_half = coupon_pct / D(2)
    y_half = yield_pct / D(200)
    accrued = cpn_half * (D(dcs) / D(e_days))

    if n_coupons <= 1:
        dirty = (redemption + cpn_half) / (D(1) + y_half * D(dsm) / D(e_days))
    else:
        dsc_frac = D(dsc) / D(e_days)
        dirty = redemption / _pow(D(1) + y_half, D(n_coupons - 1) + dsc_frac)
        for k in range(1, n_coupons + 1):
            dirty += cpn_half / _pow(D(1) + y_half, D(k - 1) + dsc_frac)
    return round10(dirty - accrued), round10(accrued)


def bond_ytm(settlement, maturity, coupon_pct: Decimal, price: Decimal,
             redemption: Decimal = D(100)) -> Decimal:
    """Yield to maturity solved by bisection against bond_price (the manual
    doesn't publish a closed form for YTM either)."""
    def f(y: Decimal) -> Decimal:
        clean, _ = bond_price(settlement, maturity, coupon_pct, y, redemption)
        return clean - price

    lo, hi = D(0), D(100)
    flo, fhi = f(lo), f(hi)
    if (flo > 0) == (fhi > 0):
        raise Error5CompoundInterest()
    for _ in range(100):
        mid = (lo + hi) / 2
        fmid = f(mid)
        if fmid == 0 or (hi - lo) < D("1E-9"):
            return round10(mid)
        if (fmid > 0) == (flo > 0):
            lo, flo = mid, fmid
        else:
            hi = mid
    return round10((lo + hi) / 2)


def demo() -> None:
    # 12C manual-style mortgage: PV=100000, n=360(30y monthly), i=0.5%/mo -> PMT
    pmt = solve_pmt(D(360), D("0.00625"), D(100000), D(0), begin=False)
    assert pmt < 0, pmt  # cash-flow sign convention: payment is an outflow
    pv_back = solve_pv(D(360), D("0.00625"), pmt, D(0), begin=False)
    assert abs(pv_back - D(100000)) < D("0.01"), pv_back

    i = solve_i(D(360), D(100000), pmt, D(0), begin=False)
    assert abs(i - D("0.00625")) < D("0.0001"), i

    # Manual's own worked example (p.33-34): $450 loan, 60 days, 7% ->
    # 5.25 (360-basis) / 5.18 (365-basis rounded to display places).
    i360, i365 = simple_interest(D(60), D(-450), D("0.07"))
    assert i360 == D("5.25"), i360
    assert round(i365, 2) == D("5.18"), i365

    from datetime import date
    # Par-bond identity: priced exactly on a coupon date with yield==coupon,
    # clean price must be exactly 100 (hand-verifiable, not code-echoing).
    price, accrued = bond_price(date(2020, 1, 1), date(2025, 1, 1), D(6), D(6))
    assert price == D(100), price
    assert accrued == D(0), accrued

    # Manual's own worked example (p.68-69): declining-balance depreciation,
    # $10,000 cost / $500 salvage / 5yr life / 200% factor.
    dpn1, rbv1 = depreciation_db(D(10000), D(200), D(5))
    assert dpn1 == D(4000) and rbv1 == D(6000), (dpn1, rbv1)
    dpn2, rbv2 = depreciation_db(rbv1, D(200), D(5))
    assert dpn2 == D(2400) and rbv2 - D(500) == D(3100), (dpn2, rbv2)  # RDV = RBV - salvage

    # Manual's own worked example (p.54-55): AMORT, 25yr/13.25%/$50,000
    # mortgage, PMT=-573.35, first year of payments.
    i_monthly = round10(D("13.25") / 12) / 100
    interest, principal, new_pv = amortize(12, D(50000), D("-573.35"), i_monthly, False, 1, 2)
    assert interest == D("-6608.89"), interest
    assert principal == D("-271.31"), principal
    assert new_pv == D("49728.69"), new_pv

    print("financial: OK")


if __name__ == "__main__":
    demo()
