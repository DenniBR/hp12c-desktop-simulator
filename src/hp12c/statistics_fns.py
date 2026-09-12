"""Statistics: Sigma+/Sigma-, mean, weighted mean, std dev, linear regression.

Accumulators live in registers R1..R6 = n, Sx, Sy, Sx2, Sy2, Sxy (this mapping
is inferred from the Error 2 condition table in Appendix C, which references
exactly these six sums by name -- not guessed). Formulas are Appendix D's
"Statistics" section, transcribed exactly.
"""
from dataclasses import dataclass
from decimal import Decimal

from .decimal_ctx import round10
from .errors import Error2Statistics

D = Decimal


@dataclass
class Accumulators:
    n: Decimal = D(0)
    sx: Decimal = D(0)
    sy: Decimal = D(0)
    sx2: Decimal = D(0)
    sy2: Decimal = D(0)
    sxy: Decimal = D(0)


def accumulate(acc: Accumulators, x: Decimal, y: Decimal) -> Decimal:
    acc.n += 1
    acc.sx += x
    acc.sy += y
    acc.sx2 = round10(acc.sx2 + x * x)
    acc.sy2 = round10(acc.sy2 + y * y)
    acc.sxy = round10(acc.sxy + x * y)
    return acc.n


def cancel(acc: Accumulators, x: Decimal, y: Decimal) -> Decimal:
    acc.n -= 1
    acc.sx -= x
    acc.sy -= y
    acc.sx2 = round10(acc.sx2 - x * x)
    acc.sy2 = round10(acc.sy2 - y * y)
    acc.sxy = round10(acc.sxy - x * y)
    return acc.n


def mean(acc: Accumulators):
    if acc.n == 0:
        raise Error2Statistics()
    return round10(acc.sx / acc.n), round10(acc.sy / acc.n)


def weighted_mean(acc: Accumulators) -> Decimal:
    """xw = sum(weight*item)/sum(weight). Confirmed by the manual's own
    worked example (p.81-82: "item ENTER weight Sigma+", i.e. weight is
    keyed into X, item into Y before pressing Sigma+) -- so weight
    accumulates into Sx (not Sy as an earlier version of this function
    assumed) and sum(weight*item) is Sxy. Validated bit-for-bit against that
    example (four gas-station purchases -> 1.19 cost/gallon)."""
    if acc.sx == 0:
        raise Error2Statistics()
    return round10(acc.sxy / acc.sx)


def _variance_terms(acc: Accumulators):
    vx = acc.n * acc.sx2 - acc.sx * acc.sx
    vy = acc.n * acc.sy2 - acc.sy * acc.sy
    return vx, vy


def std_dev(acc: Accumulators):
    if acc.n <= 1:
        raise Error2Statistics()
    vx, vy = _variance_terms(acc)
    if vx < 0 or vy < 0:
        raise Error2Statistics()
    denom = acc.n * (acc.n - 1)
    sx = round10((vx / denom).sqrt())
    sy = round10((vy / denom).sqrt())
    return sx, sy


def linear_estimate_y(acc: Accumulators, x: Decimal):
    """Returns (y_hat, r)."""
    vx, vy = _variance_terms(acc)
    if acc.n == 0 or vx == 0:
        raise Error2Statistics()
    b = (acc.n * acc.sxy - acc.sx * acc.sy) / vx
    a = (acc.sy - b * acc.sx) / acc.n
    y_hat = round10(a + b * x)
    r = _correlation(acc, vx, vy)
    return y_hat, r


def linear_estimate_x(acc: Accumulators, y: Decimal):
    """Returns (x_hat, r)."""
    vx, vy = _variance_terms(acc)
    if acc.n == 0 or vx == 0:
        raise Error2Statistics()
    b = (acc.n * acc.sxy - acc.sx * acc.sy) / vx
    a = (acc.sy - b * acc.sx) / acc.n
    if b == 0:
        raise Error2Statistics()
    x_hat = round10((y - a) / b)
    r = _correlation(acc, vx, vy)
    return x_hat, r


def _correlation(acc: Accumulators, vx: Decimal, vy: Decimal) -> Decimal:
    denom = vx * vy
    if denom <= 0:
        raise Error2Statistics()
    numerator = acc.n * acc.sxy - acc.sx * acc.sy
    return round10(numerator / denom.sqrt())


def demo() -> None:
    acc = Accumulators()
    for x, y in [(D(1), D(2)), (D(2), D(4)), (D(3), D(6))]:
        accumulate(acc, x, y)
    mx, my = mean(acc)
    assert mx == D(2) and my == D(4), (mx, my)
    y_hat, r = linear_estimate_y(acc, D(4))
    assert y_hat == D(8), y_hat
    assert abs(r - D(1)) < D("0.0001"), r
    print("statistics_fns: OK")


if __name__ == "__main__":
    demo()
