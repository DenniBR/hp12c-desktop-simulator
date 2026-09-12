"""HP-12C Error 0-9 conditions (Appendix C of the user's guide)."""


class CalcError(Exception):
    """Base for all 'Error N' display conditions. code is the digit shown."""
    code: int
    label: str

    def __str__(self) -> str:
        return f"Error {self.code}"


class Error0Math(CalcError):
    code, label = 0, "Mathematics"


class Error1Overflow(CalcError):
    code, label = 1, "Storage Register Overflow"


class Error2Statistics(CalcError):
    code, label = 2, "Statistics"


class Error3IRR(CalcError):
    code, label = 3, "IRR (no convergence)"


class Error4Memory(CalcError):
    code, label = 4, "Memory"


class Error5CompoundInterest(CalcError):
    code, label = 5, "Compound Interest"


class Error6StorageRegisters(CalcError):
    code, label = 6, "Storage Registers"


class Error7IRR(CalcError):
    code, label = 7, "IRR (no sign change)"


class Error8Calendar(CalcError):
    code, label = 8, "Calendar"


class Error9Service(CalcError):
    code, label = 9, "Service"


ERRORS_BY_CODE = {
    e.code: e
    for e in [
        Error0Math, Error1Overflow, Error2Statistics, Error3IRR, Error4Memory,
        Error5CompoundInterest, Error6StorageRegisters, Error7IRR,
        Error8Calendar, Error9Service,
    ]
}
