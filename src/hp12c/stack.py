"""The RPN automatic memory stack (X, Y, Z, T, LAST X).

Rules below are taken from Appendix A of the hp-12c user's guide, verbatim in
behavior (not paraphrase-guessed):

* ENTER copies X into Y and lifts the stack; terminates digit entry.
* Stack lift is suppressed for the number entered right after one of: ENTER,
  CLx, Sigma+, Sigma-, 12x, 12/ (the last two store into a financial register,
  same reason storing into n/i/PV/PMT/FV via STO also suppresses lift).
* One-number functions (1/x, sqrt, LN, e^x, n!, RND, INTG, FRAC, CHS) replace X,
  save old X to LAST X (except CHS, which is a digit-entry key, not a
  "function"), and do NOT drop the stack.
* Two-number functions (+, -, x, /, y^x) use X and Y, save old X to LAST X, and
  DROP the stack (Z->Y, T->Z, T retained) after placing the result in X.
* Percentage functions (%, Delta%, %T) use X and Y, save old X to LAST X, but
  neither lift nor drop the stack (Y/Z/T unchanged) -- this is a documented
  exception to the two-number rule.
* x<>y exchanges X/Y only. R-down rotates the whole stack. LAST X recall lifts
  (subject to the same suppression rule) then copies LAST X into X.
"""
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from typing import Callable, Optional

from .decimal_ctx import round10, Overflow

# Keys whose *own* action suppresses stack lift for the NEXT number entered.
# (12x / 12/ and "STO into a financial register" are applied externally via
# suppress_next_lift() since they live in financial.py / engine.py.)


@dataclass
class _Entry:
    """Digit-entry scratch state while a number is being typed in."""
    sign: str = ""
    integer: str = "0"
    frac: str = ""
    has_dot: bool = False
    eex: bool = False
    exp_sign: str = ""
    exp_digits: str = ""

    def mantissa_text(self) -> str:
        text = self.sign + (self.integer or "0")
        if self.has_dot:
            text += "." + self.frac
        return text

    def value(self) -> Decimal:
        try:
            mantissa = Decimal(self.mantissa_text() or "0")
        except InvalidOperation:
            mantissa = Decimal(0)
        if self.eex and self.exp_digits:
            exp = int(self.exp_sign + self.exp_digits)
            mantissa = mantissa * (Decimal(10) ** exp)
        return mantissa


class RPNStack:
    def __init__(self) -> None:
        self.x = Decimal(0)
        self.y = Decimal(0)
        self.z = Decimal(0)
        self.t = Decimal(0)
        self.last_x = Decimal(0)
        self.stack_lift_enabled = True
        self._entry: Optional[_Entry] = None

    # ---- digit entry -----------------------------------------------
    @property
    def entry_active(self) -> bool:
        return self._entry is not None

    def _begin_entry_if_needed(self) -> _Entry:
        if self._entry is None:
            if self.stack_lift_enabled:
                self._lift()
            self._entry = _Entry()
            self.stack_lift_enabled = True  # suppression, if any, is consumed
        return self._entry

    def press_digit(self, digit: str) -> None:
        e = self._begin_entry_if_needed()
        if e.eex:
            if len(e.exp_digits) < 2:
                e.exp_digits += digit
        else:
            if e.has_dot:
                if len(e.integer) + len(e.frac) < 10:
                    e.frac += digit
            else:
                if e.integer == "0":
                    e.integer = digit
                else:
                    if len(e.integer) < 10:
                        e.integer += digit
        self.x = round10(e.value())

    def press_dot(self) -> None:
        e = self._begin_entry_if_needed()
        if not e.eex:
            e.has_dot = True
        self.x = round10(e.value())

    def press_eex(self) -> None:
        e = self._begin_entry_if_needed()
        e.eex = True

    def press_chs(self) -> None:
        """CHS: sign-alteration digit-entry key. Does not lift/drop, does not
        touch LAST X, and does not suppress the next lift (it's not in the
        6-key suppression list)."""
        if self._entry is not None:
            e = self._entry
            if e.eex:
                e.exp_sign = "" if e.exp_sign == "-" else "-"
            else:
                e.sign = "" if e.sign == "-" else "-"
            self.x = round10(e.value())
        else:
            self.x = round10(-self.x)

    def terminate_entry(self) -> None:
        self._entry = None

    # ---- stack primitives -------------------------------------------
    def _lift(self) -> None:
        self.t = self.z
        self.z = self.y
        self.y = self.x

    def _drop(self) -> None:
        self.y = self.z
        self.z = self.t
        # t remains (constant-preserving drop)

    def suppress_next_lift(self) -> None:
        self.stack_lift_enabled = False

    def store_and_suppress(self, value: Decimal) -> None:
        """Like enter_value, but leaves lift suppressed afterward (used by
        12x/12/ which store into a financial register AND update the
        display, yet are on the manual's 6-key stack-lift-suppression
        list -- unlike a plain RCL/compute result)."""
        self.terminate_entry()
        if self.stack_lift_enabled:
            self._lift()
        self.x = round10(value)
        self.stack_lift_enabled = False

    def press_enter(self) -> None:
        self.terminate_entry()
        self._lift()
        self.stack_lift_enabled = False

    def press_clx(self) -> None:
        self.terminate_entry()
        self.x = Decimal(0)
        self.stack_lift_enabled = False

    def exchange_xy(self) -> None:
        self.terminate_entry()
        self.x, self.y = self.y, self.x

    def roll_down(self) -> None:
        self.terminate_entry()
        self.x, self.y, self.z, self.t = self.y, self.z, self.t, self.x

    def recall_last_x(self) -> None:
        self.terminate_entry()
        if self.stack_lift_enabled:
            self._lift()
        self.x = self.last_x
        self.stack_lift_enabled = True

    def enter_value(self, value: Decimal) -> None:
        """Used by RCL / financial results being placed into X like a typed
        number: obeys the current lift-suppression flag, then re-enables lift
        for whatever comes after (RCL is not a suppressing key)."""
        self.terminate_entry()
        if self.stack_lift_enabled:
            self._lift()
        self.x = round10(value)
        self.stack_lift_enabled = True

    # ---- function application ----------------------------------------
    def apply_unary(self, fn: Callable[[Decimal], Decimal]) -> Decimal:
        self.terminate_entry()
        old_x = self.x
        result = round10(fn(old_x))
        self.last_x = old_x
        self.x = result
        self.stack_lift_enabled = True
        return result

    def apply_binary(self, fn: Callable[[Decimal, Decimal], Decimal]) -> Decimal:
        self.terminate_entry()
        old_x = self.x
        result = round10(fn(self.y, old_x))
        self.last_x = old_x
        self._drop()
        self.x = result
        self.stack_lift_enabled = True
        return result

    def apply_percent(self, fn: Callable[[Decimal, Decimal], Decimal]) -> Decimal:
        """%, Delta%, %T: use X & Y, save LAST X, but do NOT lift or drop."""
        self.terminate_entry()
        old_x = self.x
        result = round10(fn(self.y, old_x))
        self.last_x = old_x
        self.x = result
        self.stack_lift_enabled = True
        return result

    def snapshot(self) -> dict:
        return {"x": self.x, "y": self.y, "z": self.z, "t": self.t, "last_x": self.last_x}


def demo() -> None:
    s = RPNStack()
    # 2 ENTER 3 + -> X=5, Y=5 (drop keeps T duplicated into Z/Y after 1 op)
    s.press_digit("2")
    s.press_enter()
    s.press_digit("3")
    s.apply_binary(lambda y, x: y + x)
    assert s.x == Decimal(5), s.x

    # ENTER suppresses next lift: 1 ENTER 2 -> Y=1 X=2 (not Y=1,Z=1 shift)
    s2 = RPNStack()
    s2.press_digit("1")
    s2.press_enter()
    s2.press_digit("2")
    assert s2.x == Decimal(2) and s2.y == Decimal(1), (s2.x, s2.y)

    # Percent does not drop the stack: 200 ENTER 10 % -> X=20, Y=200 unchanged
    s3 = RPNStack()
    s3.press_digit("2"); s3.press_digit("0"); s3.press_digit("0")
    s3.press_enter()
    s3.press_digit("1"); s3.press_digit("0")
    s3.apply_percent(lambda y, x: y * x / 100)
    assert s3.x == Decimal(20) and s3.y == Decimal(200), (s3.x, s3.y)

    # Chain calc: 3 ENTER ENTER ENTER 84000 x2 -> constant in T survives drop
    s4 = RPNStack()
    s4.press_digit("2")
    s4.press_enter(); s4.press_enter(); s4.press_enter()
    s4.press_digit("8"); s4.press_digit("4"); s4.press_digit("0"); s4.press_digit("0"); s4.press_digit("0")
    s4.apply_binary(lambda y, x: y * x)
    assert s4.x == Decimal(168000), s4.x
    s4.press_digit("0")  # fresh entry after a binary op (lift enabled) - types over via new entry
    print("stack: OK")


if __name__ == "__main__":
    demo()
