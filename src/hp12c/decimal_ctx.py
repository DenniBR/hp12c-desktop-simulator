"""Fixed-precision arithmetic matching the HP-12C's 10-digit BCD register.

The manual states: "all calculations in your hp 12c are performed with full
10-digit numbers" (Section 5, p.71) and defines overflow/underflow explicitly
(p.73): magnitude > 9.999999999e99 clamps to that value (signed) and halts;
magnitude < 1e-99 (nonzero) becomes exactly 0 without halting.

We do NOT claim bit-exact firmware BCD emulation. We use decimal.Decimal at
high working precision for each single operation's internal math, then round
the *stored* result down to 10 significant digits with ROUND_HALF_UP (the
manual's documented rounding rule: 3rd digit 5-9 rounds up, 0-4 truncates).
This reproduces the calculator's *observable* rounding/overflow behavior even
though the underlying representation (binary-coefficient Decimal) differs
from the real BCD hardware.
"""
from decimal import Decimal, ROUND_HALF_UP, getcontext

SIG_DIGITS = 10
MAX_MAGNITUDE = Decimal("9.999999999E99")
MIN_MAGNITUDE = Decimal("1E-99")

getcontext().prec = 40


class Overflow(Exception):
    """Raised to signal the halted/clamped state after an overflow."""
    def __init__(self, clamped: Decimal):
        self.clamped = clamped
        super().__init__(f"overflow: clamped to {clamped}")


def round10(value: Decimal) -> Decimal:
    """Round a Decimal to the calculator's 10-significant-digit register width.

    Applies overflow clamp (raises Overflow, caller decides how to surface it)
    and underflow-to-zero, then rounds to 10 significant digits, half-up.
    """
    if value == 0:
        return Decimal(0)

    sign = 1 if value >= 0 else -1
    magnitude = abs(value)

    if magnitude > MAX_MAGNITUDE:
        clamped = sign * MAX_MAGNITUDE
        raise Overflow(clamped)

    if magnitude < MIN_MAGNITUDE:
        return Decimal(0)

    exponent = magnitude.adjusted()  # power of 10 of the leading digit
    quantum = Decimal(1).scaleb(exponent - (SIG_DIGITS - 1))
    rounded = value.quantize(quantum, rounding=ROUND_HALF_UP)
    return rounded


def demo() -> None:
    assert round10(Decimal("2") + Decimal("3")) == Decimal("5")
    assert round10(Decimal("1") / Decimal("3")) == Decimal("0.3333333333")
    assert round10(Decimal("14.87456320")).quantize(Decimal("0.01")) == Decimal("14.87")
    try:
        round10(Decimal("1E100"))
        raise AssertionError("expected Overflow")
    except Overflow as exc:
        assert exc.clamped == MAX_MAGNITUDE
    assert round10(Decimal("1E-100")) == Decimal(0)
    print("decimal_ctx: OK")


if __name__ == "__main__":
    demo()
