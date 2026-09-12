"""Display formatting: Standard (FIX n) and Scientific (SCI n).

Facts confirmed in the manual (Section 5, p.71-73):
* Default on reset: Standard format, 2 decimal places.
* f 0-9 sets Standard with that many decimal places (0-9).
* Rounding for display is round-half-up (3rd digit 5-9 rounds up, 0-4 down) --
  this is a VIEW-only rounding; the underlying register keeps 10 significant
  digits regardless of what's displayed.
* f . sets Scientific notation: mantissa is the first 7 significant digits
  (one nonzero digit before the point), 2-digit signed exponent.
* Standard format auto-switches to Scientific for a value that doesn't fit,
  then returns to Standard once a value fits again. The manual does not give
  the exact fits/doesn't-fit threshold in numeric form, so the switch rule
  implemented here (integer-digit-count overflow) is an approximation --
  flagged NOT VERIFIED in docs/COMPATIBILITY.md.
* There is NO Engineering (ENG) mode on the 12C Classic (confirmed absent from
  the full manual text) -- NOT IMPLEMENTED, by design, not by oversight.
* Overflow / underflow clamps are handled in decimal_ctx.round10, not here.
"""
from decimal import Decimal, ROUND_HALF_UP

D = Decimal


def _round_places(value: Decimal, places: int) -> Decimal:
    quantum = Decimal(1).scaleb(-places)
    return value.quantize(quantum, rounding=ROUND_HALF_UP)


def format_standard(value: Decimal, places: int, decimal_char: str = ".") -> str:
    rounded = _round_places(value, places)
    sign = "-" if rounded < 0 else ""
    rounded = abs(rounded)
    text = f"{rounded:,.{places}f}"
    int_part, _, frac_part = text.partition(".")
    out = sign + int_part
    if places > 0:
        out += decimal_char + frac_part
    else:
        out += decimal_char  # 12C shows a trailing point even with 0 decimals
    return out


def format_scientific(value: Decimal, places: int, decimal_char: str = ".") -> str:
    if value == 0:
        mantissa_text = "0" + (decimal_char + "0" * places if places else "")
        return f"{mantissa_text} 00"
    sign = "-" if value < 0 else ""
    magnitude = abs(value)
    exponent = magnitude.adjusted()
    mantissa = magnitude.scaleb(-exponent)
    mantissa = _round_places(mantissa, places)
    if mantissa >= 10:  # rounding pushed it to e.g. 10.000000 -> renormalize
        mantissa = mantissa / 10
        exponent += 1
    mantissa_text = f"{mantissa:.{places}f}".replace(".", decimal_char)
    exp_sign = "-" if exponent < 0 else " "
    return f"{sign}{mantissa_text}{exp_sign}{abs(exponent):02d}"


def fits_standard(value: Decimal, places: int) -> bool:
    if value == 0:
        return True
    magnitude = abs(value)
    integer_digits = max(magnitude.adjusted() + 1, 1)
    return integer_digits + places <= 10 and magnitude >= Decimal(1).scaleb(-places) / 2 or magnitude == 0


class Display:
    def __init__(self) -> None:
        self.mode = "STD"  # or "SCI"
        self.places = 2
        self.decimal_char = "."

    def render(self, value: Decimal) -> str:
        if self.mode == "SCI":
            # mantissa is "the first seven digits" (p.72): 1 leading + up to
            # 6 decimals, regardless of a larger FIX place count carried over.
            return format_scientific(value, min(self.places, 6), self.decimal_char)
        if fits_standard(value, self.places):
            return format_standard(value, self.places, self.decimal_char)
        return format_scientific(value, min(self.places, 6), self.decimal_char)


def demo() -> None:
    assert format_standard(D("14.87456320"), 2) == "14.87"
    assert format_standard(D("14.87456320"), 4) == "14.8746"
    assert format_standard(D("14.87456320"), 0) == "15."
    assert format_scientific(D("14.87456320"), 6) == "1.487456 01"
    assert format_standard(D("-118.42"), 2) == "-118.42"
    assert format_standard(D("1095"), 2) == "1,095.00"
    print("display: OK")


if __name__ == "__main__":
    demo()
