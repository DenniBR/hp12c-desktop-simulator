# Pre-implementation analysis — HP-12C Classic

Primary source: *hp 12c financial calculator user's guide*, Edition 4, HP Part Number
0012C-90001 (official manual linked by the user, extracted and read page by page).
All rules below were confirmed in the manual's own text, not from generic
"financial calculator" memory. Where the manual is silent, this is stated explicitly.

## 1. Key inventory (physical map → function)

> **OUTDATED — do not use this table as a layout reference.** It is the
> historical record of the *pre-implementation* analysis, made from the
> manual's text before a measured photo of the device existed. Several
> positions here are wrong (it assigns CLEAR REG/FIN/PRGM to `f 7/8/9`, AMORT
> to `f 1`, NPV to `f 3`, x≤y to `÷`...). The real layout was established
> later by direct measurement of the reference file `hp12c.png` and lives in
> `src/hp12c/engine.py` (`F_SHIFT`/`G_SHIFT`) + `src/ui/app.py`. The
> *behavior rules* from section 2 onward remain valid — only this position
> map has been superseded. Verified in the 2026-09-12 functional audit.

| Physical key | Direct | `f` (gold) | `g` (blue) |
|---|---|---|---|
| `n` | n (periods) | — | 12× (n = 12·x, goes to n reg.) |
| `i` | i (rate) | — | 12÷ (i = x/12, goes to i reg.) |
| `PV` | PV | — | CFo (initial cash flow) |
| `PMT` | PMT | — | CFj (cash flow j) |
| `FV` | FV | — | Nj (number of flow repetitions) |
| `CHS` | sign change | — | — |
| `7` | 7 | CLEAR REG | — |
| `8` | 8 | CLEAR FIN | — |
| `9` | 9 | CLEAR PRGM | — |
| `÷` | ÷ | — | x≤y / conditional tests (programming) |
| `4` `5` `6` | digits | — | — |
| `×` | × | — | — |
| `1` | 1 | AMORT | INT (simple interest) |
| `2` | 2 | %T | %Δ |
| `3` | 3 | NPV | IRR |
| `-` `+` | arithmetic | — | — |
| `RCL` | RCL | — | — |
| `STO` | STO | — | — |
| `EEX` | EEX | — | — |
| `CLx` | Clear X | — | — |
| `÷ family` (Σ+, R↓, x≷y, ENTER) | as labeled | see below | see below |
| `ENTER` | ENTER↑ | — | LSTx |
| `x≷y` | swap X/Y | — | — |
| `R↓` | roll down | — | — |
| `Σ+` | accumulates statistics | — | Σ- (removes) |
| `1/x` | reciprocal | — | — |
| `√x` | root | — | — |
| `y^x` | power | — | — |
| `%` | x% of y | — | — |
| `.` | decimal point | FIX (decimal places) | — |
| `Σ+`..`E` (labels A-E) | program labels | — | GTO destination |
| `R/S` | run/stop program | — | P/R (program/run) |
| `GTO` | goes to line | — | memory map (`g MEM`) |
| `f` | gold prefix | — | — |
| `g` | blue prefix | — | — |
| `ON` | on/off | — | — |

Additional relevant `f`/`g` functions: `f 0-9` = fixed decimal places (FIX);
`f .` = scientific notation (SCI); `f CLx` (held down) = shows the full
10-digit mantissa; `g D.MY` / `g M.DY` = date format; `g BEG` / `f END`
(real names: `g 7`=BEG, `f 8` is actually END — confirmed via the Function
Key Index, see `E`/BEG glyphs) = advance/arrears payment mode.

## 2. Machine states

- **On/Off**: continuous memory preserves the stack, registers, program,
  display format, date format, payment mode.
- **Continuous memory reset**: (a) automatic if power was interrupted — shows
  `Pr Error` on power-up; (b) manual: powered off, hold `-`, press `ON`.
  Result: all registers zeroed; program = 8 lines of `GTO 00`;
  display = default 2 places; date = M.DY; payment = End.
- **Run mode vs Program mode**: `f P/R` toggles. When returning to Run, the
  program pointer goes back to line 00.
- **Error**: any key clears the error message and restores the state prior to
  the operation (it does not execute the function of the key that cleared the error).
- **CLEAR x / CLEAR REG / CLEAR FIN / CLEAR Σ / CLEAR PRGM / CLEAR PREFIX**: these
  are independent operations, each clearing a different subset — **never
  assume that one clears the others** (explicit user requirement, confirmed
  by the manual: CLEAR REG does not erase the program; CLx does not erase registers).

## 3. RPN stack (Appendix A — primary source, not a paraphrase)

Registers: X (display), Y, Z, T, plus LAST X (not a stack register, it is a holding register).

Exact rules:
1. `ENTER↑`: copies X→Y (stack lift), terminates digit entry. The stack always lifts.
2. **Stack lift is suppressed** (the next number entered replaces X instead of
   pushing the stack) if the last key pressed was one of these 6: `ENTER↑`,
   `CLx`, `Σ+`, `Σ-`, `12×`, `12÷`. (The last two are specific to the 12C —
   both store directly into a financial register, the same reason storing
   into a financial register via `STO n/i/PV/PMT/FV` also suppresses the
   next lift.)
3. **One-number functions** (1/x, √x, LN, e^x, n!, RND, INTG, FRAC, CHS): operate
   only on X, the result goes into X, the previous X goes to LAST X, the stack
   does **not** drop (Y/Z/T unchanged).
4. **Two-number functions** (+, −, ×, ÷, y^x): use X and Y, result in X, previous
   X → LAST X, the stack **drops** (Z→Y, T→Z, and T remains — allowing a constant).
5. **Percentage functions** (%, Δ%, %T): result in X, previous X → LAST X,
   the stack **neither drops nor lifts** — Y/Z/T unchanged. This differs from a
   normal binary function.
6. **Financial/calendar functions when computing** (n, i, PV, PMT, FV, NPV, IRR,
   DATE, ΔDYS, INT, PRICE, YTM, DEP): each has its own effect documented in a
   specific table (see Appendix A) — they do not follow the generic binary rule.
7. `x≷y`: swaps X↔Y, does not touch Z/T, is neither a lift nor a drop.
8. `R↓`: rotates X→T, T→Z, Z→Y, Y→X (circular downward).
9. `LSTx` (`g` + ENTER): lifts the stack (unless the previous key suppresses lift),
   copies LAST X into X.

## 4. Display formats

- Factory default / after reset: **Standard**, 2 decimal places.
- `f 0`–`f 9`: Standard with N decimal places (*display-only* rounding,
  **the internal 10-digit value does not change**, except when the key
  itself is one of the ones that actually round the internal value: `f RND`,
  `AMORT`, `SL`, `SOYD`, `DB`).
- Rounding rule: next digit 5–9 rounds up; 0–4 truncates
  (round-half-up, not banker's rounding).
- `f .`: scientific notation — 7-significant-digit mantissa + signed
  2-digit exponent (space = positive, `-` = negative).
- **There is no ENG (engineering) mode on the 12C Classic** — I searched "ENG" in
  the full manual (211 pages) and there is no occurrence. This is a feature of
  other HP calculators (15C/16C) or of generic financial suites, not the
  12C. **I will mark it as NOT IMPLEMENTED** rather than inventing a mode that
  does not exist on the target hardware.
- Overflow: |result| > 9.999999999×10^99 → the calculation is stopped and shows
  ±9.999999999 99 (this is not an "Error", it is a clamp).
- Underflow: |result| < 10^-99 (≠0) → the value is treated as 0, the calculation
  continues normally (no interruption).
- `f CLx` held down: shows the full mantissa (10 digits) while
  held.
- Decimal separator period/comma: switchable (hardware feature documented via
  holding `.` while powering on) — low priority, implement if time allows.

## 5. Financial functions (Appendix D — official formulas)

- **TVM without a fractional period**:
  `PV·(1+i)^n + PMT·(1+i·S)·[(1+i)^n − 1]/i + FV = 0`, S=1 (Begin) or 0 (End).
- **TVM with a fractional period (odd period)**: two documented variants —
  simple interest over the fractional period, or compound interest over the
  fractional period — distinct formulas involving INTG(n)/FRAC(n). The
  physical 12C decides which to use depending on context (the manual is not
  100% explicit about which is the default for the plain `n`/`i`/`PV`/`PMT`/`FV`
  key; I will implement the version without a fractional period as the
  main path, tested, and mark odd-period as
  **NOT VERIFIED** until real hardware fixtures exist).
- **Iterative solution of `i`**: the manual does not publish the firmware's exact
  convergence algorithm. I will implement Newton-Raphson with a bisection fallback,
  documented as **not bit-exact to the firmware**, but converging to the same
  result (10 significant digits) in the testable cases.
- **n is always rounded up** to the next integer (explicitly
  documented).
- **Amortization** (`f n` = AMORT, CONFIRMED p.54-55): `INT₁ = |PV₀·i|_RND ·
  sign(PMT)` (or 0 if j=1 and Begin), `PRN = PMT − INT`, `new PV = PV + PRN`.
  **The `_RND` rounding is to the CURRENT DISPLAY'S DECIMAL PLACES (e.g., 2),
  not to 10 significant digits** — validated bit-for-bit against the manual's
  own example (25-year mortgage, 13.25%, $50,000, PMT=-573.35: year 1 =
  -6,608.89/-271.31; year 2 = -6,570.72/-309.48). The `n` register
  **ACCUMULATES** amortized periods (starts at 0 after CLEAR FIN, adds on each
  call) — confirmed by the manual itself (":n 12.00 Total number of
  payments amortized" after amortizing 12 periods, not a decreasing term).
  Output registers: X=INT, Y=PRN, Z=previous X (count), T=previous Y
  (Appendix A p.175, not a generic lift).
- **Simple interest** (`f i` = INT, CONFIRMED p.33-34): `n` is the NUMBER OF DAYS
  (not years), `i` is the ANNUAL rate. `I360 = n·(−PV)·i/360`, `I365 =
  n·(−PV)·i/365` — the `−PV` (not `PV`) is necessary because the principal is
  stored negative (sign convention) but the interest shown is positive;
  validated bit-for-bit against the manual's example ($450, 60 days, 7% →
  5.25/5.18). Output registers: X=INT360, Y=−PV, Z=INT365, T=previous X
  — confirmed both by the Appendix A table and by the manual's own
  "f INT R↓ x≷y" sequence for viewing the 365-day basis.
- **NPV**: sum of CFj/(1+i)^j, j=0..n, supports Nj (repetitions) up to 20 stored
  distinct flows.
- **IRR**: root of NPV(i)=0. Error 3 = does not converge; Error 7 = no sign
  change in the flows (no solution).
- **Bonds** (`f` + unidentified key = PRICE/YTM, shift CONFIRMED
  p.66-67, physical key NOT CONFIRMED): yield via `i`, coupon via `PMT`,
  settlement=Y, maturity=X. PRICE also writes the result into the `PV`
  register (confirmed: "shown in the display and also is stored in the PV
  register"); accrued interest is left in Y (via x≷y). YTM reads the
  target price from the `PV` register (not `FV` — corrected from an
  initial mistake) and writes the result into `i`. Validated
  bit-for-bit/display against the manual's two examples (yield 8.25%→price
  87.62/90.31; price 88.375→yield 8.15%).
- **Depreciation** (`f` + unidentified key = SL/SOYD/DB, shift
  CONFIRMED p.68 "fV"/"fÝ"/"f#", physical key NOT CONFIRMED): cost via
  `PV`, salvage value via `FV`, useful life via `n`, factor (DB) via `i`
  (percentage); only the year number is keyed directly into X. Keystroke
  formulas, no partial period: SL: `DPN=(SBV−SAL)/L`. SOYD: `DPN=(L−j+1)/SOYD·(SBV−SAL)`,
  `SOYD=W(W+1)/2+WF`. DB: `DPNⱼ=RBVⱼ₋₁·FACT/100/L`, with `RBV` persisted in the
  `PV` register between calls (same pattern as amortization). Output:
  X=DPN, Y=RDV (remaining value **minus** salvage value, not the pure book
  value). Validated bit-for-bit against the manual's declining-balance
  example (cost 10,000/salvage 500/life 5/factor 200%: years 1-3 =
  4,000/2,400/1,440, RDV = 5,500/3,100/1,660).
- **Rate conversion**: `EFF=(1+NOM/C)^C−1` (finite compounding),
  `EFF=e^NOM−1` (continuous) — present in the appendix, dedicated keys not
  clearly identified in the Function Key Index; implement as a utility,
  mark key-based access as NOT VERIFIED.

## 6. Calendar

- **Actual basis**: `ΔDYS = f(DT2) − f(DT1)`, where
  `f(DT) = 365·year + 31·(month−1) + day + INTG(z/4) − x`, with the
  per-century leap-year rule (a century year that is a multiple of 100 is not
  a leap year, except when it is also a multiple of 400 — manual's note:
  "century (but not millennium) years are not considered leap years", i.e., it
  replicates the standard Gregorian calendar).
- **30/360 basis**: its own formula with day-31-treated-as-30 rules —
  documented exactly in Appendix D.
- D.MY / M.DY formats selectable via `g` shift, not programmable.
- Error 8: invalid date format, or (for DATE) exceeds the calculator's
  capacity, or (bonds) more than 500 years between dates / maturity before
  settlement / maturity with no matching coupon 6 months earlier (special
  rule for day 29/30/31 of certain months).

## 7. Statistics

Registers R1..R6 = n, Σx, Σy, Σx², Σy², Σxy (confirmed by the Error 2
condition, which references exactly these sums).
- Mean: `x̄=Σx/n`, `ȳ=Σy/n`.
- Weighted mean: `x̄w = Σ(weight·item)/Σweight`. Convention CONFIRMED by the
  manual's example (p.81-82, "item ENTER weight Σ+"): X=weight, Y=item at
  the moment of Σ+, hence `Σx=Σweight`, `Σy=Σitem`, `Σxy=Σ(weight·item)`, and
  `x̄w=Σxy/Σx` (not `/Σy` — an earlier version of this analysis had the
  convention inverted; corrected and validated bit-for-bit against the
  4-gas-station example, result 1.19/gallon).
- Sample standard deviation: `sx=√[(nΣx²−(Σx)²)/(n(n−1))]` (same for y). Requires
  n≥2 (Error 2 if n≤1 or a negative term from numeric cancellation).
- Linear regression: `ŷ=A+Bx`, `B=(nΣxy−ΣxΣy)/(nΣx²−(Σx)²)`, `A=ȳ−Bx̄`;
  inverse `x̂=(y−A)/B`; correlation coefficient `r` with its own formula
  (root of a product of variances).

## 8. Memory and registers

- Data registers: `R0`–`R9` and `R.0`–`R.9` (20 total, default).
- `STO`/`RCL` accept a direct register, register arithmetic
  (`STO +/-/×/÷ n`), and financial registers as a target.
- Error 4/6: register arithmetic is not allowed on `R5`-`R9`/`R.0`-`R.9`
  when part of them has been converted into program lines; a nonexistent
  or converted register → Error 6.
- `CLEAR REG`: zeroes X,Y,Z,T + all storage + statistics + financial
  registers (but **not** the program).
- `CLEAR FIN`: zeroes only the financial registers (n,i,PV,PMT,FV).
- `CLEAR Σ`: zeroes R1-R6 + the stack.
- `CLEAR PRGM`: resets program memory to 8 lines of `GTO 00`, does not touch data.

## 9. Programming

- Total combinable memory: **8 fixed program lines** + **20 data
  registers**, with dynamic conversion: for every block of 7 instructions
  beyond the 8th, the **last available data register** (starting from
  `R.9`) is converted into 7 new program lines (losing the data stored in it).
- Maximum: **99 program lines**, consuming 13 registers
  (`8 + 13×7 = 99`), leaving `R0`-`R6` (7 registers) for data.
- Line 00 contains a hidden "halt" instruction; empty lines contain `GTO 00`.
- `f P/R`: toggles Program↔Run; when returning to Run, the pointer goes to line 00.
- `R/S`: runs/pauses from the current line.
- `GTO nn`: branches to a line; labels `0`-`9`, `.0`-`.9`, `A`-`E` also serve
  as a `GTO`/implicit-call target.
- Conditional tests (`x≤y`,`x=0`, etc. under a dedicated key with a 0-9 suffix):
  skip the next line if false — I will implement the complete set (`x=0`,
  `x≠0`, `x>0`, `x<0`, `x≥0`, `x≤0`, `x=y`, `x≠y`, `x>y`, `x<y`, `x≥y`, `x≤y`).
- Error 4: more than 99 lines, or `GTO` to a nonexistent line.

## 10. Errors (Appendix C — complete, 10 categories)

Error 0 Math (÷0, ln(x≤0), √(x<0), invalid y^x, non-integer/negative x!,
etc.) · Error 1 Storage-register overflow (STO arithmetic resulting in
|value|>9.999999999e99) · Error 2 Statistics (n=0, Σx=0 where
needed, a negative variance term, n≤1 for standard deviation) · Error 3 IRR
does not converge · Error 4 Memory (>99 lines, invalid GTO, invalid
register arithmetic) · Error 5 Compound interest (conditions with no
solution — PMT≤−PV·i, i≤−100%, etc.) · Error 6 Nonexistent/converted
storage registers · Error 7 IRR with no sign change in the flows · Error 8 Calendar
(invalid date/format, exceeds capacity, coupon rules) · Error 9 Service
(hardware/self-test failure — not applicable to a simulator; I will map it
to a merely informational condition).

## 11. Test plan (`tests/hp12c-reference.json`)

Mandatory categories A–J from the brief, with cases derived directly from
the manual's own examples whenever available (these sequences and results
ALREADY ARE the official reference — when the user provides results from
physical hardware, these will be treated as additional fixtures and will
take priority over any assumption of mine in case of divergence).

## 12. Scope of this first delivery (transparency, not "100% compatible")

Implemented and tested in this round: full RPN stack, arithmetic, percentages,
TVM (case without a fractional period), amortization, simple interest, NPV/IRR,
depreciation (keystroke formulas), calendar (actual + 30/360), full
statistics, registers/STO/RCL, basic programming (GTO, R/S, labels,
conditional tests, memory expansion).

Explicitly **NOT IMPLEMENTED**: ENG mode (does not exist on the target
hardware), bonds with a non-semiannual coupon, MIRR (not a native 12C key,
it is a "solutions" example), configurable comma/period decimal separator,
`f CLx` held down showing the mantissa (low UI priority).

Explicitly **NOT VERIFIED against physical hardware**: any numeric result
until the user provides outputs from a real HP-12C for comparison —
the current tests validate against the manual's own formulas and examples,
which is a documentary check, not a hardware check.
