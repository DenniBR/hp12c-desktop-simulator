# Reference source

**Single, primary, official document**: *hp 12c financial calculator user's
guide*, Edition 4, HP Part Number 0012C-90001 — the manual linked by the user
in the briefing (`h10032.www1.hp.com/ctg/Manual/c00363319.pdf`). 211 pages,
extracted and read in full (text, not just the index) during the analysis in
`docs/ANALYSIS.md`.

No other "generic financial calculator" was used as a behavior reference. Where this simulator uses a standard library (`datetime` from Python for day differences on an "actual" basis), this is explicitly documented in `docs/COMPATIBILITY.md` with the justification for why it replaces, without loss of fidelity, the manual's formula at that specific point.

## Map: manual section → code module

| Subject | Manual section/Appendix | Module |
|---|---|---|
| RPN stack, LAST X, stack lift/drop | Appendix A | `src/hp12c/stack.py` |
| Errors 0–9 | Appendix C | `src/hp12c/errors.py`, triggered throughout `engine.py` |
| TVM, amortization, simple interest, NPV/IRR, bonds, depreciation | Appendix D | `src/hp12c/financial.py` |
| Calendar (actual and 30/360) | Appendix D | `src/hp12c/calendar_fns.py` |
| Statistics (formulas) | Appendix D + Section 6 | `src/hp12c/statistics_fns.py` |
| Program memory (8+20, expansion, limit 99) | Section 8 | `src/hp12c/memory.py` |
| Display (Standard/Scientific, rounding, overflow/underflow) | Section 5 | `src/hp12c/display.py` |
| Names/descriptions of each key | Function Key Index / Programming Key Index | `src/hp12c/engine.py` (dispatcher) |

## Why there is no hardware validation yet

The original briefing requests validation against a physical HP-12C when available, and treats this as a priority over any implementation assumption. So far, no real hardware results have been provided — the 58 cases in `tests/hp12c-reference.json` are all derived from the manual itself (Appendix D formulas or numerical examples already solved in the text) or from independently verifiable mathematical identities (e.g., bond at par ⇒ price = 100). This is **documentary** validation, not **hardware** validation — the distinction is explicitly made in `docs/COMPATIBILITY.md` so as not to claim precision that has not yet been achieved.
