"""Data storage registers, financial registers, and program-memory allocation.

Register facts below are from Appendix C (Error 4/6 conditions) and Section 8
(Programming Basics), not assumed:

* 20 data registers by default: R0-R9 and R.0-R.9.
* Register ARITHMETIC (STO +/-/x/(divide)) only works on R0-R4; attempting it
  on R5-R9 or R.0-R.9 is Error 4.
* Plain STO/RCL works on any register that exists and hasn't been converted
  to program memory; otherwise Error 6.
* Program memory starts at 8 lines; every time an instruction is keyed past
  the current capacity, the highest remaining register (consumption order:
  R.9, R.8, ... R.0, R9, R8, ... R0) is converted into 7 more lines. Capacity
  tops out at 99 lines (8 + 13*7), which consumes 13 registers and leaves
  R0-R6 for data -- matching the manual's own worked example exactly.
"""
from dataclasses import dataclass, field
from decimal import Decimal

from .errors import Error4Memory, Error6StorageRegisters
from .statistics_fns import Accumulators

D = Decimal

REGISTER_CONSUMPTION_ORDER = (
    [f"R.{d}" for d in range(9, -1, -1)] + [f"R{d}" for d in range(9, -1, -1)]
)
BASE_PROGRAM_LINES = 8
LINES_PER_REGISTER = 7
MAX_PROGRAM_LINES = 99
ARITHMETIC_REGISTERS = {"R0", "R1", "R2", "R3", "R4"}


@dataclass
class Financial:
    n: Decimal = D(0)
    i: Decimal = D(0)
    pv: Decimal = D(0)
    pmt: Decimal = D(0)
    fv: Decimal = D(0)
    begin: bool = False


@dataclass
class CashFlows:
    """CFo/CFj/Nj storage for NPV/IRR (up to 20 distinct flows)."""
    amounts: list = field(default_factory=list)  # Decimal, index 0 = CFo
    counts: list = field(default_factory=list)   # int, Nj (default 1)

    def clear(self):
        self.amounts.clear()
        self.counts.clear()

    def store_initial(self, value: Decimal):
        self.amounts = [value]
        self.counts = [1]

    def store_next(self, value: Decimal):
        if len(self.amounts) >= 20:
            raise Error6StorageRegisters()
        self.amounts.append(value)
        self.counts.append(1)

    def set_last_count(self, n: int):
        if not self.amounts or n < 1 or n > 99 or n != int(n):
            raise Error6StorageRegisters()
        self.counts[-1] = n


class Memory:
    def __init__(self) -> None:
        self.data = {name: D(0) for name in REGISTER_CONSUMPTION_ORDER}
        self.converted_count = 0
        self.financial = Financial()
        self.cashflows = CashFlows()

    # ---- program memory sizing ----------------------------------------
    @property
    def program_capacity(self) -> int:
        return BASE_PROGRAM_LINES + LINES_PER_REGISTER * self.converted_count

    @property
    def registers_available(self) -> list:
        return REGISTER_CONSUMPTION_ORDER[self.converted_count:]

    def ensure_capacity(self, needed_lines: int) -> None:
        while needed_lines > self.program_capacity:
            if self.program_capacity >= MAX_PROGRAM_LINES:
                raise Error4Memory()
            self.converted_count += 1

    def register_exists(self, name: str) -> bool:
        return name in self.registers_available

    # ---- STO/RCL --------------------------------------------------------
    def sto(self, name: str, value: Decimal) -> None:
        if not self.register_exists(name):
            raise Error6StorageRegisters()
        self.data[name] = value

    def rcl(self, name: str) -> Decimal:
        if not self.register_exists(name):
            raise Error6StorageRegisters()
        return self.data[name]

    def sto_arith(self, op, name: str, value: Decimal) -> Decimal:
        if name not in ARITHMETIC_REGISTERS or not self.register_exists(name):
            raise Error4Memory()
        result = op(self.data[name], value)
        self.data[name] = result
        return result

    # ---- statistics view over R1..R6 -------------------------------------
    def stats_view(self) -> Accumulators:
        return Accumulators(
            n=self.data["R1"], sx=self.data["R2"], sy=self.data["R3"],
            sx2=self.data["R4"], sy2=self.data["R5"], sxy=self.data["R6"],
        )

    def stats_store(self, acc: Accumulators) -> None:
        self.data["R1"], self.data["R2"], self.data["R3"] = acc.n, acc.sx, acc.sy
        self.data["R4"], self.data["R5"], self.data["R6"] = acc.sx2, acc.sy2, acc.sxy

    # ---- clears -----------------------------------------------------------
    def clear_reg(self) -> None:
        for name in self.data:
            self.data[name] = D(0)
        self.financial = Financial(begin=self.financial.begin)
        self.cashflows.clear()

    def clear_fin(self) -> None:
        self.financial = Financial(begin=self.financial.begin)
        self.cashflows.clear()

    def clear_sigma(self) -> None:
        for r in ("R1", "R2", "R3", "R4", "R5", "R6"):
            self.data[r] = D(0)

    def clear_prgm(self) -> None:
        self.converted_count = 0


def demo() -> None:
    m = Memory()
    m.sto("R0", D(42))
    assert m.rcl("R0") == D(42)
    try:
        m.rcl("R.5")  # exists by default (20 registers), should work
    except Error6StorageRegisters:
        raise AssertionError("R.5 should exist by default")

    # force expansion: need 15 lines -> converts R.9, R.8 (8+7=15 exactly with 1 register)
    m.ensure_capacity(15)
    assert m.converted_count == 1, m.converted_count
    assert not m.register_exists("R.9")

    # max out: 99 lines needs 13 registers converted
    m2 = Memory()
    m2.ensure_capacity(99)
    assert m2.converted_count == 13, m2.converted_count
    assert m2.register_exists("R0") and m2.register_exists("R6")
    assert not m2.register_exists("R7")
    try:
        m2.ensure_capacity(100)
        raise AssertionError("expected Error4Memory")
    except Error4Memory:
        pass

    try:
        m.sto_arith(lambda a, b: a + b, "R9", D(1))
        raise AssertionError("expected Error4Memory for arithmetic on R9")
    except Error4Memory:
        pass

    print("memory: OK")


if __name__ == "__main__":
    demo()
