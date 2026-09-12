# Compatibility — HP-12C Classic Simulator

Target model: **HP-12C Classic** (not Platinum). Primary source:
*hp 12c financial calculator user's guide*, Edition 4, HP Part Number
0012C-90001 (official manual linked by the user in the original briefing).

## How to read this document

* **VERIFIED (manual)** = the behavior/formula was confirmed in the text
  of the manual (cited in `docs/ANALYSIS.md`) and covered by test case(s) in
  `tests/hp12c-reference.json`.
* **NOT VERIFIED (hardware)** = there is still no test case with output
  from a real physical HP-12C. The entire project remains in this category until
  the user provides results from a real device — at that point those
  results become priority fixtures (see policy in
  `docs/ANALYSIS.md` §12 and in the original briefing).
* **NOT IMPLEMENTED** = a function that the manual says the real calculator has
  but that this simulator does not reproduce yet.
* **DOCUMENTED SIMPLIFICATION** = implemented, but with an explicit design
  choice where the manual was ambiguous or where the exact physical position
  of a key could not be confirmed.

Current suite: **126/126 cases passing** (`python tests/run_tests.py`), covering
categories A–M. No known unresolved discrepancy is being hidden — what follows
is the complete list of known gaps.

**2026-09-12 — v1.0.1 root-cause audit (stale digit entry)**: a user report
that `STO` followed by `EEX` raised a fake Error 0 led to a deeper audit of
every prefix-starter key (`F`, `G`, `STO`, `RCL`, `GTO`) rather than a
one-off patch. Two distinct root causes were found and fixed, both in
`engine.py`:
1. Every prefix-continuation branch (`_continue_sto`, `_continue_rcl`,
   `_continue_gto`, the `.`/arithmetic sub-states) ended with a blanket
   `raise ValueError` for any real keyboard key it didn't specifically
   expect, which the dispatcher turned into a fake "Error 0" — the exact
   bug class already fixed for `f`/`g` in the previous audit, just missed
   for `STO`/`RCL`/`GTO`. Fixed the same way: a real key with no valid
   target for that prefix cancels the prefix as a harmless no-op.
2. Deeper bug: typing a number, then pressing `STO` (or `RCL`, `F`, `G`)
   and completing its second key, left the ORIGINAL number's digit-entry
   buffer open — so the next digit typed silently concatenated onto the
   old number instead of starting fresh (`10 STO 5` then typing `7` showed
   `107`, not `7`). Every other function key on this keyboard (`ENTER`,
   `CLx`, the arithmetic keys, `x<>y`, `R-down`) already terminates digit
   entry as the first thing it does; the prefix-starter keys were the one
   place that deferred it to whichever leaf branch the second key resolved
   to — and some leaf branches never did it, especially on an error path
   (the entry stayed open even after the error was cleared). Fixed at the
   single point where `F`/`G`/`STO`/`RCL`/`GTO` are recognized, so it now
   holds regardless of what the second key turns out to be, valid or not.

An exhaustive sweep (every prefix × all 38 UI-reachable keys, both for the
"fake error" class and the "stale entry" class) found zero remaining
instances of either bug. 14 new regression cases (category M) cover both,
including `STO -> EEX` itself, the exact stale-entry repro, and the
error-then-clear-then-fresh-number case that would have hidden a
half-fix.

**2026-09-12 — LCD visual pass**: the on-screen LCD's active segments read
as pale/washed-out and the digit spacing looked like "loose separate
drawings" rather than one number. Direct pixel measurement of the reference
photo (`hp12c.png`) found the glass is 50.1% of the case width, positioned
16.1% of the case width from the left edge (not centered — there is nearly
twice as much cream to its right as to its left), and 9.84% of the case
width tall; the on-screen LCD box was resized and repositioned to match
(348×69 at a 112px left offset, was 550×80 centered — see `LCD_W` in
`app.py`). The reference photo's display itself is powered off (flat glass,
zero contrast even at 4x boost), so no digit segment color/thickness could
be pixel-measured from it — that part is a legibility correction, not a
photo measurement, and is documented as such in `app.py`: active segments
are now much darker/near-black, inactive segments sit much closer to the
glass color (a bare ghost, not a second visible gray), and the inter-digit
gap was cut from 25% to 12% of digit width. No calculation logic changed.

**2026-09-12 — keyboard functional audit**: active scan of all
39 keys × {direct, f, g}, executing every route for real, plus flows driven
only by key sequences that the UI can emit. It found **8 bugs**, all fixed,
and **30 new test cases** (category L + gaps in B/C/D/E/F). The most serious bug:
`f P/R` entered program mode but **never exited** — the `f` key was recorded
as a program line instead of acting as a prefix, so Program mode was an
inescapable trap. The old tests did not catch this because they triggered the
internal `PR_TOGGLE` action directly, which no UI key can emit.

**2026-09-12 — fidelity audit**: a complete audit comparing each function against
the text of the manual (not against the implementation) found and fixed
**7 real discrepancies** between the previous behavior and the manual —
not merely nomenclature. Complete list and evidence for each in
`docs/ANALYSIS.md` §5; summary:

1. Simple interest (`INT`) treated `n` as years and did not divide by 360/365 —
   fixed, validated against the manual example ($450/60 days/7% → 5.25/5.18).
2. Amortization used 10-digit rounding instead of rounding to the display's
   decimal places (the `_RND` of the formula) — fixed,
   validated against the manual's 25-year example.
3. Amortization decremented `n` from a predefined term; the manual shows that
   `n` ACCUMULATES amortized periods starting from 0 — fixed.
4. Depreciation read SBV/SAL/life from the RPN stack; the manual uses PV/FV/n —
   fixed.
5. Bond YTM read the target price from the FV register; the manual uses PV —
   fixed.
6. AMORT/INT/depreciation/bond-PRICE output registers followed a generic
   stack "lift"; Appendix A's table requires a specific and different T/Z/Y/X
   mapping — fixed for all 4 functions.
7. Weighted average divided by Σy; the manual example (ENTER weight Σ+)
   shows that the weight goes into X, so the correct division is by Σx — fixed.

All 7 corrections were validated bit-by-bit (or rounded to the display,
when that is what the manual itself shows) against REAL numerical examples
from the manual — not merely against the formula. This is documentary
verification of the highest confidence available without a physical device.

## Implemented and verified against the manual

* Complete RPN stack (X,Y,Z,T,LAST X), exact stack lift/drop rules
  (Appendix A), including lift suppression by the 6 specific 12C keys
  (ENTER, CLx, Σ+, Σ-, 12×, 12÷) and by STO into a financial register.
* Arithmetic, 1/x, √x, y^x, LN, e^x, n!, RND, INTG, FRAC.
* %, Δ%, %T (with differentiated stack behavior — does not drop/lift).
* TVM without fractional periods (n, i, PV, PMT, FV), with n always rounded
  upward; solution for i by bisection (not the firmware algorithm, see
  the "Approximations" section below).
* Amortization (`f n`): period-by-period recursion from Appendix D with
  rounding to the display's decimal places, `n` accumulating amortized
  periods, exact T/Z/Y/X output registers — bit-by-bit equal to the manual's
  example (25-year mortgage/13.25%/$50,000, 2 years).
* Simple interest (`f i`): 360 and 365 bases, `n` in days, `i` annual —
  bit-by-bit equal to the manual's example ($450/60 days/7%).
* NPV / IRR with up to 20 distinct cash flows and repetitions (Nj).
* Depreciation SL/SOYD/DB (key formulas, without partial periods), inputs
  via PV/FV/n/i (not stack), RBV persisted in PV between DB calls —
  bit-by-bit equal to the manual's example (cost 10,000/salvage 500/life
  5 years/200%, 3 years).
* Bonds (PRICE/YTM) using the SIA method cited in the manual itself, inputs via
  PMT (coupon)/i (yield)/PV (target price for YTM), PRICE result also
  stored in PV — bit-by-bit (rounded to the display) equal to both examples
  in the manual, in addition to the "par bond" identity
  (coupon=yield ⇒ price=100) verified by independent calculation.
* Calendar: actual-basis ΔDYS (via Python's `datetime`, not the polynomial
  formula in the manual — see justification in `calendar_fns.py`) and 30/360
  (exact Appendix D formula). DATE (addition of days). D.MY/M.DY formats.
* Complete statistics: Σ+/Σ-, mean, weighted mean (Σxy/Σx — weight in X,
  item in Y, bit-by-bit equal to the manual's example of the 4 gas stations),
  sample standard deviation, linear regression (ŷ,r and x̂,r).
* R0–R9/R.0–R.9 registers, STO/RCL, register arithmetic restricted to
  R0–R4 (Error 4 outside these — confirmed in Appendix C, not an assumption).
* Program memory model: 8 base lines + 20 registers, expansion in blocks of
  7 lines consuming registers in the order R.9→R.0→R9→...,
  limit of 99 lines (consuming exactly 13 registers) — reproduces the
  manual's own numerical example.
* Programming: key recording (1 physical key = 1 line, as in the
  hardware), GTO, labels A–E, R/S, conditional tests (x=0/x≠0/x>0/x<0/
  x≥0/x≤0 and x=y/x≠y/x>y/x<y/x≥y/x≤y).
* Display: Standard (FIX 0–9) and Scientific (7 significant-digit
  mantissa), round-half-up rounding, overflow (clamp at
  ±9.999999999×10^99) and underflow (→0) exactly as described on p.73.
* Complete Errors 0–9 (Appendix C) with the exact conditions listed in
  the manual, not a generic list of "mathematical errors".

## NOT IMPLEMENTED (by design, not omission)

* **ENG (engineering) mode**: it does not exist on the HP-12C Classic. A search
  of the complete manual (211 pages) found no occurrence of "ENG"
  as a display mode. Implementing it would invent behavior that the
  target hardware does not have.
* **TVM with fractional periods (odd period)**: the manual documents two
  variants (simple or compound interest during the fractional period) but
  does not make clear which key is used by default without an explicit period.
  Instead of guessing, only the path without a fractional period is implemented.
* **Bonds with non-semiannual coupon / 30/360 basis for bonds**: only the
  semiannual actual/actual case is implemented.
* **Configurable decimal separator comma/period** (hardware feature via
  holding `.` while powering on): not implemented, low functional priority.
* **`f CLx` held down showing the full mantissa**: recognized as a key
  but not implemented (it is a UI feature, not a calculation feature).
* **Editing a specific cash flow by index** (storing `j` in `n` and then
  `g Nj` to correct a previously entered CFj repetition, without rebuilding
  the entire list — described on p.61-62): not implemented; the simulator
  only records CFo/CFj sequentially. Found during the audit,
  recorded here instead of being silently omitted.
* **`g` + key = MEM** (memory map: program lines used vs.
  registers available): recognized (Programming Key Index, p.206) but
  not implemented — informational only, does not affect calculation.

## DOCUMENTED SIMPLIFICATIONS

* **Physical keyboard layout**: the "core" keyboard (n/i/PV/PMT/FV, digits,
  arithmetic, ENTER, CHS, EEX, STO, RCL, GTO, f, g, x≷y, R↓, Σ+, %/Δ%/%T,
  CLx) follows the actual 12C layout. The `f`/`g` assignments of the
  financial row (`f n`=AMORT, `f i`=INT, `f PV`=NPV, `f PMT`=RND, `f FV`=IRR;
  `g n`=12×, `g i`=12÷, `g PV`=CFo, `g PMT`=CFj, `g FV`=Nj, `g CHS`=DATE,
  `g 7`=BEG, `g 8`=END) were confirmed against a reference photo
  provided by the user (not a redistributed proprietary HP image —
  only used for position/label verification, like any manual reference).
  Functions still without confirmed physical positions (advanced mathematics,
  statistics, depreciation, bonds, calendar D.MY/M.DY, `g 9`=MEM —
  not implemented, programming, CLEAR REG/FIN/Σ/PRGM) remain in a separate
  "Additional Functions" panel — more honest than risking an unverified
  physical position for those keys in the main body.
  Color palette (beige/cream body, nearly black keys, gold/blue)
  was also adjusted to match the reference.

  **2026-09-12 — physical position audit (SL/SOYD/DB/PRICE/YTM):**
  the manual documents (p.91) a 2-digit "keycode" (line, position) displayed
  for each key recorded in a program. This makes it possible to confirm position
  **without relying on the photo**, by cross-referencing independent citations
  within the text itself:

  * **DB (`f #`) — CONFIRMED**: two program listings (pp.68-69, p.141)
    show `f# ... 42 25`; separately, the text on p.91 explicitly states
    that the `%` key (glyph `b`) has keycode `25` (line 2, position 5).
    The two citations match exactly to the same key — **DB is `f` + the `%` key**,
    independently of the photo.
  * **SL (`f V`) and SOYD (`f Ý`) — POSITION CONFIRMED, BASE KEY NOT
    CONFIRMED**: the same listings show `fV...42 23` and `fÝ...42 24`
    (line 2, positions 3 and 4 — adjacent to position 5 of the `%` key,
    matching the visual grouping "%T Δ% %" in the photo). But no listing
    in the manual uses `%T` or `Δ%` by themselves to independently confirm
    WHICH unshifted label occupies these two positions — identification of
    these two labels remains supported by the photo, not by a cross-referenced
    textual citation.
  * **PRICE (`f E`) and YTM (`f S`) — NOT CONFIRMED**: no program listing
    in the manual uses the native `E`/`S` keys (the 30/360 bond program on
    pp.163-166 reimplements everything from scratch with a user-defined label,
    without touching these keys). Without a keycode to cross-reference,
    and without being able to reopen the photo for pixel-by-pixel verification,
    the physical position remains **NOT CONFIRMED**. Layout was not changed
    at the user's explicit request.
* **`i` register**: entered/displayed as a percentage (e.g., `10` for 10%),
  converted to decimal internally before entering the Appendix D formulas
  (which define i "expressed as a decimal"). Behavior confirmed by the
  footnote on p.172 regarding `100000 PV` versus `100000 PV FV`.
* ~~**Bonds — register convention**~~: **no longer a simplification**.
  Confirmed in the manual text (pp.66-67): coupon via `PMT`, yield via `i`,
  settlement=Y, maturity=X; target price for YTM via `PV`
  (not `FV` — an initial mistake in this implementation, corrected in the audit).
  What remains unconfirmed is only the **PHYSICAL POSITION** of the
  `f`+`E`/`f`+`S` key on the keyboard (see "Physical keyboard layout" above).
* **Iterative solution of `i` and YTM**: by bisection, not the firmware
  algorithm (not publicly documented). They converge to the same result with
  10 significant digits in the tested cases, but are not bit-exact to the
  hardware.
* **ΔDYS actual-basis**: calculated with Python's `datetime.date` instead of
  reimplementing the polynomial formula from Appendix D, whose correction that
  "century years are not leap years" is not accompanied by exact arithmetic
  in the extracted text. `datetime` already implements the correct Gregorian
  calendar (the same target that the manual's correction seeks), so it is
  used directly.
* **Internal precision**: `Decimal` with 40 digits of working precision per
  operation, with explicit rounding to 10 significant digits after each
  operation (mimicking the hardware's 10-digit BCD register, not binary
  IEEE-754). This reproduces observable overflow/underflow/rounding,
  but is not a bit-exact emulation of the real BCD.

## Verification

All 112 test cases are verified **against the manual** (Appendix D formulas,
examples from the text itself, or mathematically verifiable identities such as
the par-bond). **No case has been verified against a physical HP-12C.** I do not
claim "100% compatible" — only "consistent with the manufacturer's
documentary specification at the points tested". If/when the user provides
outputs from a real device, those become the primary reference (see discrepancy
policy in `docs/ANALYSIS.md`).

## Known Unresolved Discrepancies

None at the moment — every discrepancy found during development
(see commit/checkpoint history) was investigated and corrected in the
implementation, never "resolved" by adjusting the expected value without
documentary justification.
