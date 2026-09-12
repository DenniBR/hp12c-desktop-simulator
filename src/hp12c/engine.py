"""Glue: wires the stack, memory, display and financial/stat/calendar math
into one state machine driven by a stream of semantic key actions.

Verified-from-manual behaviors implemented here (see docs/ANALYSIS.md for the
page-by-page citations):
  * n/i/PV/PMT/FV: pressed while digit entry is active -> STORE; pressed
    "cold" (no entry in progress) -> COMPUTE. Derived from the footnote on
    p.172: "the stack will not lift ... following 100000$ [store], but will
    lift ... following 100000 $M [store then compute]" -- i.e. storing
    suppresses the next lift, computing does not.
  * 12x / 12/ / CFo / CFj / Nj: unconditional stores (never compute).
  * Program recording: one physical keystroke = one program line (matches
    the manual's own line-count math for its example programs).
  * STO +/-/x/(divide) register arithmetic is restricted to R0-R4 (Error 4
    otherwise) -- Appendix C, not a guess.
"""
import operator
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation

from . import financial as fin
from . import calendar_fns as cal
from . import statistics_fns as stats
from .decimal_ctx import Overflow, round10
from .display import Display, _round_places
from .errors import CalcError, Error0Math, Error4Memory
from .memory import Memory
from .stack import RPNStack

D = Decimal

DIGIT_ACTIONS = {f"D{d}" for d in range(10)}
FIN_KEYS = ("N", "I", "PV", "PMT", "FV")
FIN_FIELD = {"N": "n", "I": "i", "PV": "pv", "PMT": "pmt", "FV": "fv"}
ARITH_OPS = {"ADD": operator.add, "SUB": operator.sub, "MUL": operator.mul, "DIV": operator.truediv}

# g-shift table (blue labels): matches the real 12C keyboard photo.
# 2026-09-12: added routes for the row2/row3 keys repositioned onto the main
# keypad per the reference photo (UI reorganization only -- every target
# action below already existed and was already covered by the 72-case suite;
# this only adds a NEW way to reach the same, unchanged action).
G_SHIFT = {
    "N": "TWELVE_MUL", "I": "TWELVE_DIV", "PV": "CFO", "PMT": "CFJ", "FV": "NJ",
    "CHS": "DATE", "D7": "BEG", "D8": "END",
    "ENTER": "LSTX", "SIGMA_PLUS": "SIGMA_MINUS",
    "YX": "SQRT", "INV": "EXP", "PCT_TOTAL": "LN", "DELTA_PCT": "FRAC", "PCT": "INTG",
    "EEX": "DDYS", "D4": "DMY", "D5": "MDY", "D6": "XW",
    "D1": "XHAT", "D2": "YHAT", "D3": "FACT",
    # 2026-09-12: corrected against the measured reference photo -- row3col3's
    # PRIMARY key is R-down (RDOWN), not CLEAR_PRGM; g+R-down = GTO.
    "RDOWN": "GTO",
    # 2026-09-12 (functional audit): these blue labels are printed on the keys
    # in the reference photo but had NO route -- pressing them raised a fake
    # "Error 0". x-bar/s/x<=y/x=0 were already implemented in this engine and
    # were simply unreachable; MEM/PSE/BST are documented no-ops (below).
    "D0": "XBAR", "DOT": "SDEV", "XY": "X_LE_Y", "CLX": "X_EQ_0",
    "D9": "MEM", "RS": "PSE", "SST": "BST",
}
# f-shift table (gold labels): the financial-register row's gold functions
# are AMORT/INT/NPV/RND/IRR on the real 12C keyboard, not "FIX n" -- FIX only
# applies to the digit keys 0-9, handled separately in _continue_f.
F_SHIFT = {
    "N": "AMORT", "I": "INT_SIMPLE", "PV": "NPV", "PMT": "RND", "FV": "IRR",
    "RS": "PR_TOGGLE", "XY": "CLEAR_FIN", "CLX": "CLEAR_REG",
    # 2026-09-12: corrected against the measured reference photo -- row3col2's
    # PRIMARY key is SST (not implemented, see the SST no-op below), and its
    # gold f-shift is CLEAR SIGMA (was wrongly attached directly to the key
    # itself before). row3col3's PRIMARY is R-down; its gold f-shift is
    # CLEAR_PRGM (was wrongly the key's own primary before).
    "SST": "CLEAR_SIGMA", "RDOWN": "CLEAR_PRGM",
    # BOND/DEPRECIATION group (row 2): position now confirmed by the photo,
    # not just the manual keycodes -- these 5 actions already existed and
    # were already tested (C-007/007b/007c/007d, C-010/011/012); this only
    # adds the route the photo shows, no new computation.
    "YX": "BOND_PRICE", "INV": "BOND_YTM",
    "PCT_TOTAL": "SL", "DELTA_PCT": "SOYD", "PCT": "DB",
    # 2026-09-12 (functional audit): CLEAR PREFIX is gold-printed on ENTER in
    # the reference photo and is one of the manual's independent CLEAR
    # operations, but had no route -- it raised a fake "Error 0".
    "ENTER": "CLEAR_PREFIX",
}

# Every action a physical key on this keyboard can emit. Used to tell a
# prefix pressed before a key that simply has no shifted function (harmless
# on real hardware -- the prefix is just consumed) apart from a genuinely
# unknown action string, which stays an error so a typo'd route still fails
# loudly instead of silently doing nothing.
KEYBOARD_ACTIONS = {
    "ADD", "CHS", "CLX", "D0", "D1", "D2", "D3", "D4", "D5", "D6", "D7", "D8", "D9",
    "DELTA_PCT", "DIV", "DOT", "EEX", "ENTER", "F", "FV", "G", "I", "INV", "MUL", "N",
    "PCT", "PCT_TOTAL", "PMT", "PV", "RCL", "RDOWN", "RS", "SIGMA_PLUS", "SST", "STO",
    "SUB", "XY", "YX",
}


@dataclass
class ProgramState:
    recording: bool = False
    lines: list = field(default_factory=list)
    pointer: int = 0
    running: bool = False
    held_prefix: str | None = None  # f/g pressed in Program mode, not yet committed to a line


class Engine:
    def __init__(self) -> None:
        self.stack = RPNStack()
        self.mem = Memory()
        self.disp = Display()
        self.date_format = "M.DY"
        self.error: CalcError | None = None
        self.pending_prefix: str | None = None
        self.program = ProgramState()

    # ------------------------------------------------------------ input --
    def press(self, action: str) -> None:
        if self.error is not None:
            self.error = None  # any key clears an error display without acting
            return
        if self.program.recording and action not in ("PR_TOGGLE", "CLEAR_PRGM"):
            self._press_recording(action)
            return
        self._dispatch(action)

    def _press_recording(self, action: str) -> None:
        """In Program mode almost every keystroke becomes a program line, but
        f P/R (leave Program mode) and f CLEAR PRGM must still EXECUTE -- the
        manual's own Run/Program toggle. The prefix therefore has to be
        tracked here as well: recording a bare "F" line the moment it is
        pressed makes the following P/R unrecognisable, and you can enter
        Program mode and never get back out. The held prefix is committed as
        its own line only once the next key proves it is not one of those two
        escapes (one keystroke = one line still holds)."""
        held = self.program.held_prefix
        if held == "F" and F_SHIFT.get(action) in ("PR_TOGGLE", "CLEAR_PRGM"):
            self.program.held_prefix = None
            self._dispatch_plain(F_SHIFT[action])
            return
        if held is not None:
            self._record(held)
            self.program.held_prefix = None
        if action in ("F", "G"):
            self.program.held_prefix = action
            return
        self._record(action)

    def _record(self, action: str) -> None:
        needed = self.program.pointer + 1
        self.mem.ensure_capacity(needed)
        lines = self.program.lines
        if self.program.pointer < len(lines):
            lines[self.program.pointer] = action
        else:
            lines.append(action)
        self.program.pointer += 1

    # ------------------------------------------------------- dispatch -----
    def _dispatch(self, action: str) -> None:
        try:
            self._dispatch_unsafe(action)
        except CalcError as exc:
            self.error = exc
        except Overflow as exc:
            self.stack.x = exc.clamped
        except (InvalidOperation, ZeroDivisionError, ValueError):
            self.error = Error0Math()

    def _dispatch_unsafe(self, action: str) -> None:
        if self.pending_prefix is not None:
            prefix, self.pending_prefix = self.pending_prefix, None
            self._continue_prefix(prefix, action)
            return
        if action in ("F", "G", "STO", "RCL", "GTO", "TEST0", "TESTXY"):
            # Every other function key on this keyboard terminates digit entry
            # the moment it is pressed (ENTER, CLx, arithmetic, x<>y, R-down
            # all do it as their first act) -- these prefix-starters are no
            # different, they just need a second keystroke to know WHICH
            # function. Terminating here, not deferred to whichever leaf
            # branch the second key resolves to, is what makes this hold even
            # when that second key turns out to be invalid and raises an
            # error (e.g. STO into a register arithmetic can't reach): the
            # stale entry can no longer leak into the number typed next.
            self.stack.terminate_entry()
            self.pending_prefix = action
            return
        self._dispatch_plain(action)

    # --------------------------------------------------------- plain -----
    def _dispatch_plain(self, action: str) -> None:
        if action in DIGIT_ACTIONS:
            self.stack.press_digit(action[1:]); return
        if action == "DOT":
            self.stack.press_dot(); return
        if action == "CHS":
            self.stack.press_chs(); return
        if action == "EEX":
            self.stack.press_eex(); return
        if action == "ENTER":
            self.stack.press_enter(); return
        if action == "CLX":
            self.stack.press_clx(); return
        if action == "XY":
            self.stack.exchange_xy(); return
        if action == "RDOWN":
            self.stack.roll_down(); return
        if action in ("SST", "BST", "PSE", "MEM"):
            # Single-step / back-step / pause / memory-status are not
            # implemented. They are honest no-ops, not fake computations --
            # and specifically NOT "Error 0", which would claim a math error
            # that never happened. Their shifted partners (CLEAR_SIGMA on
            # f+SST, P/R on f+R/S) are real and tested.
            return
        if action == "CLEAR_PREFIX":
            # By the time this runs the prefix that selected it has already
            # been consumed, so clearing prefixes is all there is to do. It
            # touches no stack, register or program state (manual: the CLEAR
            # operations are independent of one another).
            self.pending_prefix = None
            return

        if action == "ADD":
            self.stack.apply_binary(lambda y, x: y + x); return
        if action == "SUB":
            self.stack.apply_binary(lambda y, x: y - x); return
        if action == "MUL":
            self.stack.apply_binary(lambda y, x: y * x); return
        if action == "DIV":
            self.stack.apply_binary(self._safe_div); return

        if action == "SQRT":
            self.stack.apply_unary(self._safe_sqrt); return
        if action == "INV":
            self.stack.apply_unary(self._safe_inv); return
        if action == "YX":
            self.stack.apply_binary(self._safe_pow); return
        if action == "LN":
            self.stack.apply_unary(self._safe_ln); return
        if action == "EXP":
            self.stack.apply_unary(lambda x: fin._pow(D("2.718281828459045235360287"), x)); return
        if action == "FACT":
            self.stack.apply_unary(self._safe_factorial); return
        if action == "RND":
            self.stack.apply_unary(lambda x: _round_places(x, self.disp.places)); return
        if action == "INTG":
            self.stack.apply_unary(self._intg); return
        if action == "FRAC":
            self.stack.apply_unary(lambda x: x - self._intg(x)); return

        if action == "PCT":
            self.stack.apply_percent(lambda y, x: y * x / D(100)); return
        if action == "DELTA_PCT":
            self.stack.apply_percent(self._safe_delta_pct); return
        if action == "PCT_TOTAL":
            self.stack.apply_percent(self._safe_pct_total); return

        if action in FIN_KEYS:
            self._fin_key_direct(action); return
        if action == "TWELVE_MUL":
            n = round10(self.stack.x * 12)
            self.mem.financial.n = n
            self.stack.store_and_suppress(n)
            return
        if action == "TWELVE_DIV":
            i_pct = round10(self.stack.x / 12)
            self.mem.financial.i = i_pct / D(100)
            self.stack.store_and_suppress(i_pct)
            return
        if action == "CFO":
            self.mem.cashflows.store_initial(self.stack.x); self.stack.suppress_next_lift(); return
        if action == "CFJ":
            self.mem.cashflows.store_next(self.stack.x); self.stack.suppress_next_lift(); return
        if action == "NJ":
            self.mem.cashflows.set_last_count(int(self.stack.x)); self.stack.suppress_next_lift(); return
        if action == "LSTX":
            self.stack.recall_last_x(); return

        if action == "SIGMA_PLUS":
            self._sigma(+1); return
        if action == "SIGMA_MINUS":
            self._sigma(-1); return
        if action == "XBAR":
            acc = self.mem.stats_view()
            mx, my = stats.mean(acc)
            self.stack.enter_value(mx); self.stack.y = my; return
        if action == "SDEV":
            acc = self.mem.stats_view()
            sx, sy = stats.std_dev(acc)
            self.stack.enter_value(sx); self.stack.y = sy; return
        if action == "YHAT":
            acc = self.mem.stats_view()
            y_hat, r = stats.linear_estimate_y(acc, self.stack.x)
            self.stack.enter_value(y_hat); self.stack.y = r; return
        if action == "XHAT":
            acc = self.mem.stats_view()
            x_hat, r = stats.linear_estimate_x(acc, self.stack.x)
            self.stack.enter_value(x_hat); self.stack.y = r; return
        if action == "XW":
            acc = self.mem.stats_view()
            self.stack.enter_value(stats.weighted_mean(acc)); return

        if action == "NPV":
            self.stack.enter_value(fin.npv(self.mem.financial.i, self.mem.cashflows.amounts, self.mem.cashflows.counts)); return
        if action == "IRR":
            irr_pct = fin.irr(self.mem.cashflows.amounts, self.mem.cashflows.counts)
            self.mem.financial.i = irr_pct / D(100)
            self.stack.enter_value(irr_pct)
            return
        if action == "AMORT":
            # Register layout confirmed against Appendix A's table (p.175)
            # AND the worked example on p.54-55 (25yr/13.25%/$50,000 loan):
            # T=old Y, Z=old X (the count just amortized), Y=principal,
            # X=interest. The n register ACCUMULATES periods amortized so
            # far (starts at 0 after CLEAR FIN, +=count each press) -- confirmed
            # by "12f! ... :n 12.00 Total number of payments amortized" in
            # that same example (n is not a preset term counting down).
            count = int(self.stack.x)
            old_x, old_y = self.stack.x, self.stack.y
            f = self.mem.financial
            period_start = int(f.n) + 1
            interest, principal, new_pv = fin.amortize(
                count, f.pv, f.pmt, f.i, f.begin, period_start, self.disp.places)
            self.mem.financial.pv = new_pv
            self.mem.financial.n = round10(f.n + count)
            self.stack.terminate_entry()
            self.stack.t = old_y
            self.stack.z = old_x
            self.stack.y = principal
            self.stack.x = interest
            self.stack.last_x = old_x
            self.stack.stack_lift_enabled = True
            return
        if action == "INT_SIMPLE":
            # Register layout confirmed against Appendix A (p.175: T=old X,
            # Z=INT365, Y=-PV, X=INT360) AND validated against the worked
            # example "fINTd~ -> 365-day basis" (p.20-21): after INT, R-down
            # then x<>y surfaces INT365 in X -- which only works out with
            # this exact T/Z/Y/X assignment, not a generic stack lift.
            i360, i365 = fin.simple_interest(self.mem.financial.n, self.mem.financial.pv, self.mem.financial.i)
            old_x = self.stack.x
            self.stack.terminate_entry()
            self.stack.t = old_x
            self.stack.z = i365
            self.stack.y = -self.mem.financial.pv
            self.stack.x = i360
            self.stack.last_x = old_x
            self.stack.stack_lift_enabled = True
            return

        if action in ("SL", "SOYD", "DB"):
            # Confirmed p.68: cost via PV, salvage via FV, life via n,
            # declining-balance factor (%) via i; only the year number j is
            # keyed directly (X). Output (Appendix A p.175): X=DPN, Y=RDV/RBV,
            # Z=old X (year j), T=old Y -- not a generic stack lift.
            f = self.mem.financial
            old_x, old_y = self.stack.x, self.stack.y
            period = old_x
            if action == "SL":
                dpn, secondary = fin.depreciation_sl(f.pv, f.fv, f.n, period)
            elif action == "SOYD":
                dpn, secondary = fin.depreciation_soyd(f.pv, f.fv, f.n, period)
            else:
                dpn, rbv = fin.depreciation_db(f.pv, f.i * D(100), f.n)
                self.mem.financial.pv = rbv  # book value persists as the next call's rbv_prev
                secondary = round10(rbv - f.fv)  # RDV = book value minus salvage (p.68)
            self.stack.terminate_entry()
            self.stack.t = old_y
            self.stack.z = old_x
            self.stack.y = secondary
            self.stack.x = dpn
            self.stack.last_x = old_x
            self.stack.stack_lift_enabled = True
            return

        if action == "BOND_PRICE":
            # Confirmed p.66-67: yield via i, coupon via PMT, settlement=Y,
            # maturity=X, fE -> "shown in display AND stored in the PV
            # register"; accrued interest reachable via x<>y. Register
            # layout per Appendix A (p.175): T=old Y(settlement), Z=old
            # X(maturity), Y=accrued, X=price -- not a generic stack lift.
            old_x, old_y = self.stack.x, self.stack.y
            settlement = cal.parse_date(old_y, self.date_format)
            maturity = cal.parse_date(old_x, self.date_format)
            clean, accrued = fin.bond_price(settlement, maturity, self.mem.financial.pmt, self.mem.financial.i * D(100))
            self.mem.financial.pv = clean
            self.stack.terminate_entry()
            self.stack.t = old_y
            self.stack.z = old_x
            self.stack.y = accrued
            self.stack.x = clean
            self.stack.last_x = old_x
            self.stack.stack_lift_enabled = True
            return
        if action == "BOND_YTM":
            # Confirmed p.67: quoted price via PV (not FV -- fixed from an
            # earlier wrong guess), coupon via PMT, settlement=Y, maturity=X,
            # fS -> "shown in display and also stored in the i register".
            settlement = cal.parse_date(self.stack.y, self.date_format)
            maturity = cal.parse_date(self.stack.x, self.date_format)
            ytm_pct = fin.bond_ytm(settlement, maturity, self.mem.financial.pmt, self.mem.financial.pv)
            self.mem.financial.i = ytm_pct / D(100)
            self.stack.enter_value(ytm_pct)
            return

        if action == "DATE":
            base = cal.parse_date(self.stack.y, self.date_format)
            days = int(self.stack.x)
            newdate = cal.add_days(base, days)
            self.stack.enter_value(cal.format_date(newdate, self.date_format)); return
        if action == "DDYS":
            # Appendix A stack table: X = dDYS(actual basis), Y = dDYS(30-day
            # basis) -- actual is the primary/displayed result.
            d1 = cal.parse_date(self.stack.y, self.date_format)
            d2 = cal.parse_date(self.stack.x, self.date_format)
            actual = cal.actual_days_between(d1, d2)
            d360 = cal.days_360(d1, d2)
            self.stack.enter_value(D(actual)); self.stack.y = D(d360); return

        if action == "BEG":
            self.mem.financial.begin = True; return
        if action == "END":
            self.mem.financial.begin = False; return
        if action == "DMY":
            self.date_format = "D.MY"; return
        if action == "MDY":
            self.date_format = "M.DY"; return

        if action == "CLEAR_REG":
            self.mem.clear_reg(); self.stack.x = self.stack.y = self.stack.z = self.stack.t = D(0); return
        if action == "CLEAR_FIN":
            self.mem.clear_fin(); return
        if action == "CLEAR_SIGMA":
            self.mem.clear_sigma(); self.stack.x = self.stack.y = self.stack.z = self.stack.t = D(0); return
        if action == "CLEAR_PRGM":
            self.mem.clear_prgm(); self.program.lines = []; self.program.pointer = 0; return

        if action in ("X_LE_Y", "X_EQ_0"):
            # The two conditional tests printed on the reference keyboard
            # (g x<>y, g CLx). Like every 12C test they only have a visible
            # effect inside a running program: skip the next line if false.
            truth = self.stack.x <= self.stack.y if action == "X_LE_Y" else self.stack.x == 0
            self._conditional(truth)
            return

        if action == "PR_TOGGLE":
            self.program.recording = not self.program.recording
            self.program.held_prefix = None
            if not self.program.recording:
                self.program.pointer = 0
            return
        if action == "RS":
            self._run_program(); return

        if action.startswith("LBL_"):
            if self.program.running:
                return  # label reached by fallthrough: no-op marker
            self.program.pointer = self._label_line(action[4:])
            self._run_program()
            return

        raise ValueError(f"unhandled action {action}")

    # -------------------------------------------------- prefixed dispatch--
    def _continue_prefix(self, prefix: str, action: str) -> None:
        if prefix == "F":
            self._continue_f(action); return
        if prefix == "G":
            # g-shift targets (CFO/CFJ/Nj/12x/12/,LSTx,Sigma-,D.MY/M.DY) are
            # ordinary function keys, not among the manual's digit-entry/
            # prefix exemptions -- pressing them terminates digit entry.
            shifted = G_SHIFT.get(action)
            if shifted is None:
                if action in KEYBOARD_ACTIONS:
                    return  # real key with no blue function: prefix consumed, nothing happens
                raise ValueError(f"no g-shift for {action}")
            self.stack.terminate_entry()
            if shifted == "GTO":
                # GTO is a prefix-starter (needs a following line/label), not
                # a plain one-shot action -- hand off to the same GTO state
                # machine a direct GTO keypress would enter.
                self.pending_prefix = "GTO"
                return
            self._dispatch_plain(shifted); return
        if prefix == "STO":
            self._continue_sto(action); return
        if prefix == "RCL":
            self._continue_rcl(action); return
        if prefix == "STO_DOT":
            if action in DIGIT_ACTIONS:
                self.mem.sto(f"R.{action[1:]}", self.stack.x)
                self.stack.terminate_entry()
                self.stack.suppress_next_lift(); return
            if action in KEYBOARD_ACTIONS:
                return  # incomplete STO . <digit>: cancelled, not a math error
            raise ValueError("STO . needs a digit")
        if prefix == "RCL_DOT":
            if action in DIGIT_ACTIONS:
                self.stack.enter_value(self.mem.rcl(f"R.{action[1:]}")); return
            if action in KEYBOARD_ACTIONS:
                return  # incomplete RCL . <digit>: cancelled, not a math error
            raise ValueError("RCL . needs a digit")
        if prefix.startswith("STO_ARITH:"):
            self._continue_sto_arith(prefix.split(":", 1)[1], action); return
        if prefix.startswith("STO_ARITH_DOT:"):
            op_name = prefix.split(":", 1)[1]
            if action in DIGIT_ACTIONS:
                self.mem.sto_arith(ARITH_OPS[op_name], f"R.{action[1:]}", self.stack.x)
                self.stack.terminate_entry(); return
            if action in KEYBOARD_ACTIONS:
                return  # incomplete STO <op> . <digit>: cancelled, not a math error
            raise ValueError("STO-arithmetic . needs a digit")
        if prefix == "GTO":
            self._continue_gto(action); return
        if prefix.startswith("GTO_D1:"):
            first_digit = prefix.split(":", 1)[1]
            if action in DIGIT_ACTIONS:
                line_no = int(first_digit + action[1:])
                self.program.pointer = line_no
                return
            if action in KEYBOARD_ACTIONS:
                return  # incomplete GTO <d1><d2>: cancelled, not a math error
            raise ValueError("GTO needs two digits")
        if prefix in ("TEST0", "TESTXY"):
            self._continue_test(prefix, action); return
        raise ValueError(f"unknown prefix state {prefix}")

    def _continue_f(self, action: str) -> None:
        if action in F_SHIFT:
            self.stack.terminate_entry()
            self._dispatch_plain(F_SHIFT[action]); return
        if action in DIGIT_ACTIONS:
            self.stack.terminate_entry()
            self.disp.mode = "STD"; self.disp.places = int(action[1:]); return
        if action == "DOT":
            self.stack.terminate_entry()
            self.disp.mode = "SCI"; return
        if action in KEYBOARD_ACTIONS:
            return  # real key with no gold function: prefix consumed, nothing happens
        raise ValueError(f"no f-shift for {action}")

    def _continue_sto(self, action: str) -> None:
        if action in ARITH_OPS:
            self.pending_prefix = f"STO_ARITH:{action}"; return
        if action == "DOT":
            self.pending_prefix = "STO_DOT"; return
        if action in FIN_KEYS:
            # PV/PMT/N/i/FV are ordinary function keys (not digit-entry/
            # prefix-exempt), so using one as STO's target terminates entry.
            self.stack.terminate_entry()
            value = self.stack.x / D(100) if action == "I" else self.stack.x
            setattr(self.mem.financial, FIN_FIELD[action], value)
            self.stack.suppress_next_lift(); return
        if action in DIGIT_ACTIONS:
            self.mem.sto(f"R{action[1:]}", self.stack.x)
            self.stack.terminate_entry()
            self.stack.suppress_next_lift(); return
        if action in KEYBOARD_ACTIONS:
            return  # real key that is not a valid STO target: prefix cancelled, not a math error
        raise ValueError(f"bad STO target {action}")

    def _continue_rcl(self, action: str) -> None:
        if action == "DOT":
            self.pending_prefix = "RCL_DOT"; return
        if action == "I":
            self.stack.terminate_entry()
            self.stack.enter_value(self.mem.financial.i * D(100)); return
        if action in FIN_KEYS:
            self.stack.terminate_entry()
            self.stack.enter_value(getattr(self.mem.financial, FIN_FIELD[action])); return
        if action in DIGIT_ACTIONS:
            self.stack.enter_value(self.mem.rcl(f"R{action[1:]}")); return
        if action in KEYBOARD_ACTIONS:
            return  # real key that is not a valid RCL target: prefix cancelled, not a math error
        raise ValueError(f"bad RCL target {action}")

    def _continue_sto_arith(self, op_name: str, action: str) -> None:
        op = ARITH_OPS[op_name]
        if action == "DOT":
            self.pending_prefix = f"STO_ARITH_DOT:{op_name}"; return
        if action in DIGIT_ACTIONS:
            self.mem.sto_arith(op, f"R{action[1:]}", self.stack.x)
            self.stack.terminate_entry(); return
        if action in KEYBOARD_ACTIONS:
            return  # incomplete STO <op> <digit>: prefix cancelled, not a math error
        raise ValueError("bad STO-arithmetic register")

    def _continue_gto(self, action: str) -> None:
        if action.startswith("LBL_"):
            self.stack.terminate_entry()
            self.program.pointer = self._label_line(action[4:]); return
        if action in DIGIT_ACTIONS:
            self.pending_prefix = f"GTO_D1:{action[1:]}"; return
        if action in KEYBOARD_ACTIONS:
            return  # real key that is not a valid GTO target: prefix cancelled, not a math error
        raise ValueError(f"bad GTO target {action}")

    def _continue_test(self, prefix: str, action: str) -> None:
        if action not in DIGIT_ACTIONS:
            if action in KEYBOARD_ACTIONS:
                return  # real key that is not a valid test selector: prefix cancelled
            raise ValueError("test selector must be a digit 0-5")
        idx = int(action[1:])
        ops = ["EQ", "NE", "GT", "LT", "GE", "LE"]
        if idx >= len(ops):
            return  # digit 6-9: not a valid test index, prefix cancelled, not a math error
        op = ops[idx]
        x, y = self.stack.x, self.stack.y
        other = D(0) if prefix == "TEST0" else y
        truth = {
            "EQ": x == other, "NE": x != other, "GT": x > other,
            "LT": x < other, "GE": x >= other, "LE": x <= other,
        }[op]
        self._conditional(truth)

    def _conditional(self, truth: bool) -> None:
        if not truth and self.program.running:
            self.program.pointer += 1  # skip next line

    # --------------------------------------------------------- helpers ----
    def _fin_key_direct(self, action: str) -> None:
        """i is keyed/displayed as a PERCENTAGE (e.g. "1" for 1%, matching
        real hardware) but stored and used internally as a decimal fraction
        -- financial.py's formulas all take i as a decimal, per Appendix D's
        own definition ("i = periodic interest rate, expressed as a
        decimal")."""
        field = FIN_FIELD[action]
        if self.stack.entry_active:
            value = self.stack.x
            self.stack.terminate_entry()
            setattr(self.mem.financial, field, value / D(100) if action == "I" else value)
            self.stack.suppress_next_lift()
            return
        f = self.mem.financial
        begin = f.begin
        if action == "N":
            result = fin.solve_n(f.i, f.pv, f.pmt, f.fv, begin)
        elif action == "I":
            result = fin.solve_i(f.n, f.pv, f.pmt, f.fv, begin)
        elif action == "PV":
            result = fin.solve_pv(f.n, f.i, f.pmt, f.fv, begin)
        elif action == "PMT":
            result = fin.solve_pmt(f.n, f.i, f.pv, f.fv, begin)
        else:
            result = fin.solve_fv(f.n, f.i, f.pv, f.pmt, begin)
        setattr(self.mem.financial, field, result)
        self.stack.enter_value(result * D(100) if action == "I" else result)

    def _sigma(self, direction: int) -> None:
        acc = self.mem.stats_view()
        x, y = self.stack.x, self.stack.y
        n = stats.accumulate(acc, x, y) if direction > 0 else stats.cancel(acc, x, y)
        self.mem.stats_store(acc)
        self.stack.terminate_entry()
        self.stack.last_x = x
        self.stack.x = n
        self.stack.suppress_next_lift()

    def _intg(self, x: Decimal) -> Decimal:
        return x.to_integral_value(rounding="ROUND_DOWN") if x >= 0 else -((-x).to_integral_value(rounding="ROUND_DOWN"))

    def _safe_div(self, y: Decimal, x: Decimal) -> Decimal:
        if x == 0:
            raise Error0Math()
        return y / x

    def _safe_inv(self, x: Decimal) -> Decimal:
        if x == 0:
            raise Error0Math()
        return D(1) / x

    def _safe_sqrt(self, x: Decimal) -> Decimal:
        if x < 0:
            raise Error0Math()
        return x.sqrt()

    def _safe_ln(self, x: Decimal) -> Decimal:
        if x <= 0:
            raise Error0Math()
        return x.ln()

    def _safe_pow(self, y: Decimal, x: Decimal) -> Decimal:
        if y == 0 and x <= 0:
            raise Error0Math()
        if y < 0 and x != x.to_integral_value():
            raise Error0Math()
        return fin._pow(y, x)

    def _safe_factorial(self, x: Decimal) -> Decimal:
        if x != x.to_integral_value() or x < 0:
            raise Error0Math()
        n = int(x)
        result = D(1)
        for k in range(2, n + 1):
            result *= k
        return result

    def _safe_delta_pct(self, y: Decimal, x: Decimal) -> Decimal:
        if y == 0:
            raise Error0Math()
        return (x - y) / y * D(100)

    def _safe_pct_total(self, y: Decimal, x: Decimal) -> Decimal:
        if y == 0:
            raise Error0Math()
        return x / y * D(100)

    def _label_line(self, label: str) -> int:
        marker = f"LBL_{label}"
        for idx, line in enumerate(self.program.lines):
            if line == marker:
                return idx
        raise Error4Memory()

    def _run_program(self) -> None:
        self.program.running = True
        steps = 0
        try:
            while self.program.pointer < len(self.program.lines):
                action = self.program.lines[self.program.pointer]
                self.program.pointer += 1
                if action == "RS":
                    break
                self._dispatch(action)
                steps += 1
                if steps > 100000:
                    raise Error4Memory()
        finally:
            self.program.running = False

    # ------------------------------------------------------------ output -
    def display_text(self) -> str:
        if self.error is not None:
            return f"Error {self.error.code}"
        return self.disp.render(self.stack.x)


def demo() -> None:
    e = Engine()
    for a in ["D2", "ENTER", "D3", "ADD"]:
        e.press(a)
    assert e.stack.x == D(5), e.stack.x

    # from the user's brief: 10 ENTER 2 / ; 5 +
    e2 = Engine()
    for a in ["D1", "D0", "ENTER", "D2", "DIV"]:
        e2.press(a)
    assert e2.stack.x == D(5), e2.stack.x
    e2.press("D5"); e2.press("ADD")
    assert e2.stack.x == D(10), e2.stack.x

    e3 = Engine()
    for a in ["D1", "D0", "D0", "ENTER", "D2", "D0", "PCT"]:
        e3.press(a)
    assert e3.stack.x == D(20), e3.stack.x

    e4 = Engine()
    for a in ["D2", "D5", "D0", "CHS"]:
        e4.press(a)
    assert e4.stack.x == D(-250), e4.stack.x

    # STO / RCL round trip
    e5 = Engine()
    e5.press("D4"); e5.press("D2"); e5.press("STO"); e5.press("D5")
    e5.press("CLX"); e5.press("RCL"); e5.press("D5")
    assert e5.stack.x == D(42), e5.stack.x

    # register arithmetic restricted to R0-R4 (Error 4 on R5+)
    e6 = Engine()
    e6.press("D1"); e6.press("STO"); e6.press("D5")
    e6.press("D2"); e6.press("STO"); e6.press("ADD"); e6.press("D5")
    assert e6.error is not None and e6.error.code == 4, e6.error

    # simple program: 1 ENTER + (increment), run twice via R/S loop unrolled here
    e7 = Engine()
    e7.press("PR_TOGGLE")
    e7.press("D1"); e7.press("ADD")
    e7.press("PR_TOGGLE")
    e7.press("D5"); e7.press("ENTER")
    e7.press("RS")
    assert e7.stack.x == D(6), e7.stack.x

    print("engine: OK")


if __name__ == "__main__":
    demo()
