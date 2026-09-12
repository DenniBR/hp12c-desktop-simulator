"""Calendar functions: DATE, dDYS (actual + 30/360 basis), date-format parsing.

Actual-day-basis differences (dDYS "actual") are computed with Python's
`datetime.date`, not by hand-reimplementing the manual's day-numbering
polynomial. The manual's own formula (Appendix D) needs an unspecified
"additional test...to ensure century years are not considered leap years"
correction that the extracted text does not spell out numerically; Python's
`date` already implements the true proleptic Gregorian calendar (the same
target the manual's correction exists to reach), so it is used directly here
-- correct by construction rather than an under-specified reimplementation.

The 30/360 bond-basis day count is NOT a real calendar and IS implemented
exactly per Appendix D, since there's no stdlib equivalent for that synthetic
convention.
"""
from datetime import date, timedelta
from decimal import Decimal

from .errors import Error8Calendar

WEEKDAY_ABBR = ["MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"]


def actual_days_between(d1: date, d2: date) -> int:
    return (d2 - d1).days


def add_days(d: date, days: int) -> date:
    try:
        return d + timedelta(days=days)
    except OverflowError:
        raise Error8Calendar()


def weekday_of(d: date) -> str:
    return WEEKDAY_ABBR[d.weekday()]


def add_months(d: date, months: int) -> date:
    """Add whole calendar months, clamping the day into the target month
    (e.g. Aug 31 - 6 months -> Feb 28/29). Used for bond semiannual coupon
    date schedules."""
    month_index = d.month - 1 + months
    year = d.year + month_index // 12
    month = month_index % 12 + 1
    day = d.day
    while True:
        try:
            return date(year, month, day)
        except ValueError:
            day -= 1


def days_360(d1: date, d2: date) -> int:
    """30/360 bond-basis day count, exactly per Appendix D."""
    y1, m1, dd1 = d1.year, d1.month, d1.day
    y2, m2, dd2 = d2.year, d2.month, d2.day

    z1 = 30 if dd1 == 31 else dd1
    if dd2 == 31 and dd1 in (30, 31):
        z2 = 30
    elif dd2 == 31 and dd1 < 30:
        z2 = dd2
    else:
        z2 = dd2

    f1 = 360 * y1 + 30 * m1 + z1
    f2 = 360 * y2 + 30 * m2 + z2
    return f2 - f1


def parse_date(value: Decimal, fmt: str) -> date:
    """Decode a 12C date number. fmt is 'M.DY' (MM.DDYYYY) or 'D.MY' (DD.MMYYYY)."""
    if value < 0:
        raise Error8Calendar()
    text = format(value, "f")
    if "." in text:
        left, right = text.split(".")
    else:
        left, right = text, "0"
    right = (right + "0000000")[:6]  # DDYYYY or MMYYYY, zero-padded to 6
    try:
        a = int(left)
        b_dd_or_mm = int(right[:2])
        year = int(right[2:6])
    except ValueError:
        raise Error8Calendar()
    if fmt == "M.DY":
        month, day = a, b_dd_or_mm
    elif fmt == "D.MY":
        day, month = a, b_dd_or_mm
    else:
        raise ValueError(f"unknown date format {fmt}")
    try:
        return date(year, month, day)
    except ValueError:
        raise Error8Calendar()


def format_date(d: date, fmt: str) -> Decimal:
    if fmt == "M.DY":
        left, right = d.month, d.day
    elif fmt == "D.MY":
        left, right = d.day, d.month
    else:
        raise ValueError(f"unknown date format {fmt}")
    text = f"{left}.{right:02d}{d.year:04d}"
    return Decimal(text)


def demo() -> None:
    d1 = date(2004, 6, 1)
    d2 = date(2005, 12, 31)
    assert actual_days_between(d1, d2) == (d2 - d1).days
    assert days_360(date(2008, 1, 1), date(2008, 1, 31)) == 30
    assert weekday_of(date(2026, 9, 11)) == "FRI"
    dt = parse_date(Decimal("10.011994"), "M.DY")
    assert dt == date(1994, 10, 1), dt
    assert format_date(dt, "M.DY") == Decimal("10.011994")
    print("calendar_fns: OK")


if __name__ == "__main__":
    demo()
