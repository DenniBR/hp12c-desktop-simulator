"""Tkinter desktop UI for the HP-12C Classic simulator.

Visual layout: a "core" keypad (6x6) that mirrors the real 12C's physical
key positions for the keys whose behavior AND position are both confirmed
from the manual (digits, ENTER, CHS, EEX, arithmetic, n/i/PV/PMT/FV, STO,
RCL, GTO, f, g, x<>y, R-down, Sigma+, %, Delta%, %T, CLx) -- plus a clearly
separated "extended functions" panel for everything else (math, stats,
depreciation, bonds, calendar, programming, clears). The extended panel is
NOT claimed to match real physical key positions (see docs/COMPATIBILITY.md)
-- grouping functions there instead of guessing a fake position is the
honest choice.
"""
import sys
import tkinter as tk
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from hp12c.engine import Engine  # noqa: E402
from ui import sevenseg  # noqa: E402

CASE_BG = "#d7cbaa"        # warm cream/beige body, like the reference photo
CASE_BORDER = "#2a241a"
KEY_BG = "#28262a"         # near-black keys
KEY_FG = "#f4f1e8"
KEY_ACTIVE = "#47444a"
GOLD = "#9c6f18"           # amber gold, readable on cream (not HP's exact hue)
BLUE = "#155c8a"
LCD_BG = "#c3ccb4"
LCD_ON = "#20241a"
LCD_OFF = "#aeb69f"
EXT_BG = "#211d16"
EXT_LABEL_FG = "#a89a78"

KEYBOARD_MAP = {
    "0": "D0", "1": "D1", "2": "D2", "3": "D3", "4": "D4", "5": "D5",
    "6": "D6", "7": "D7", "8": "D8", "9": "D9", ".": "DOT",
    "+": "ADD", "-": "SUB", "*": "MUL", "/": "DIV",
    "\r": "ENTER", "\x1b": "CLX", "\x08": "CLX",
}


class Key(tk.Frame):
    def __init__(self, master, engine_callback, label, action, gold=None, blue=None, width=6):
        super().__init__(master, bg=CASE_BG)
        self.action = action
        self.callback = engine_callback
        top = tk.Label(self, text=gold or "", bg=CASE_BG, fg=GOLD, font=("Segoe UI", 7))
        top.pack(fill="x")
        self.btn = tk.Label(self, text=label, bg=KEY_BG, fg=KEY_FG, font=("Segoe UI", 10, "bold"),
                             width=width, height=2, relief="raised", bd=2, cursor="hand2")
        self.btn.pack(fill="both", expand=True)
        bottom = tk.Label(self, text=blue or "", bg=CASE_BG, fg=BLUE, font=("Segoe UI", 7))
        bottom.pack(fill="x")
        self.btn.bind("<ButtonPress-1>", self._press)
        self.btn.bind("<ButtonRelease-1>", self._release)

    def _press(self, _event=None):
        self.btn.configure(relief="sunken", bg=KEY_ACTIVE)
        self.callback(self.action)

    def _release(self, _event=None):
        self.btn.configure(relief="raised", bg=KEY_BG)

    def flash(self):
        self.btn.configure(relief="sunken", bg=KEY_ACTIVE)
        self.after(90, lambda: self.btn.configure(relief="raised", bg=KEY_BG))


def _resource_path(relative: str) -> Path:
    """Resolves a bundled asset both in dev and inside a PyInstaller --onefile
    build (which unpacks data files under sys._MEIPASS at runtime)."""
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent.parent.parent))
    return base / relative


class App:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.engine = Engine()
        root.title("HP-12C Simulator (não oficial)")
        root.configure(bg=CASE_BORDER)
        root.resizable(False, False)
        icon_path = _resource_path("assets/icon.ico")
        if icon_path.exists():
            try:
                root.iconbitmap(default=str(icon_path))
            except tk.TclError:
                pass

        self.case = tk.Frame(root, bg=CASE_BG, padx=14, pady=14)
        self.case.pack()

        self._build_display(self.case)
        self._build_core_keypad(self.case)
        self._build_extended_panel(self.case)

        root.bind("<Key>", self._on_key)
        self.refresh()

    # ---------------------------------------------------------- display --
    def _build_display(self, parent) -> None:
        frame = tk.Frame(parent, bg=CASE_BG, pady=8)
        frame.grid(row=0, column=0, columnspan=2, sticky="ew")
        self.canvas = tk.Canvas(frame, width=420, height=90, bg=LCD_BG, highlightthickness=2,
                                 highlightbackground="#4a4636")
        self.canvas.pack()
        self.annunciators = tk.Label(frame, text="", bg=CASE_BG, fg=GOLD, font=("Segoe UI", 9, "bold"))
        self.annunciators.pack(anchor="w")

    def _render_display(self) -> None:
        self.canvas.delete("all")
        text = self.engine.display_text()
        digit_w, digit_h, gap = 24, 44, 6
        total_w = sevenseg.measure(text, digit_w, gap)
        x = max(10, 410 - total_w)
        sevenseg.draw_string(self.canvas, x, 20, text, digit_w, digit_h, gap, LCD_ON, LCD_OFF)

        flags = []
        if self.engine.pending_prefix == "F":
            flags.append("f")
        if self.engine.pending_prefix == "G":
            flags.append("g")
        if self.engine.mem.financial.begin:
            flags.append("BEGIN")
        if self.engine.program.recording:
            flags.append(f"PRGM {self.engine.program.pointer:02d}")
        if self.engine.error is not None:
            flags.append(f"ERROR {self.engine.error.code}")
        self.annunciators.configure(text="   ".join(flags))

    # ------------------------------------------------------- core keypad --
    def _build_core_keypad(self, parent) -> None:
        grid = tk.Frame(parent, bg=CASE_BG)
        grid.grid(row=1, column=0, sticky="n")
        rows = [
            [("n", "N", "AMORT", "12x"), ("i", "I", "INT", "12/"), ("PV", "PV", "NPV", "CFo"),
             ("PMT", "PMT", "RND", "CFj"), ("FV", "FV", "IRR", "Nj"), ("CHS", "CHS", None, "DATE")],
            [("7", "D7", None, "BEG"), ("8", "D8", None, "END"), ("9", "D9", None, None),
             ("÷", "DIV", None, None), ("f", "F", None, None), ("g", "G", None, None)],
            [("4", "D4", None, None), ("5", "D5", None, None), ("6", "D6", None, None),
             ("×", "MUL", None, None), ("STO", "STO", None, None), ("RCL", "RCL", None, None)],
            [("1", "D1", None, None), ("2", "D2", None, None), ("3", "D3", None, None),
             ("−", "SUB", None, None), ("GTO", "GTO", None, None), ("x≷y", "XY", None, None)],
            [("0", "D0", None, None), (".", "DOT", None, None), ("EEX", "EEX", None, None),
             ("+", "ADD", None, None), ("Σ+", "SIGMA_PLUS", None, "Σ-"), ("R↓", "RDOWN", None, None)],
            [("%", "PCT", None, None), ("Δ%", "DELTA_PCT", None, None), ("%T", "PCT_TOTAL", None, None),
             ("CLx", "CLX", None, None), ("ENTER", "ENTER", None, "LSTx"), ("R/S", "RS", None, None)],
        ]
        self.keys = {}
        for r, row in enumerate(rows):
            for c, (label, action, gold, blue) in enumerate(row):
                key = Key(grid, self.press, label, action, gold, blue)
                key.grid(row=r, column=c, padx=2, pady=2)
                self.keys[action] = key

    # --------------------------------------------------- extended panel ---
    def _build_extended_panel(self, parent) -> None:
        panel = tk.Frame(parent, bg=EXT_BG, padx=8, pady=8)
        panel.grid(row=1, column=1, sticky="n", padx=(12, 0))
        tk.Label(panel, text="FUNÇÕES ADICIONAIS", bg=EXT_BG, fg=EXT_LABEL_FG,
                  font=("Segoe UI", 8, "bold")).grid(row=0, column=0, columnspan=4, sticky="w", pady=(0, 4))

        groups = [
            ("Matemática", [("1/x", "INV"), ("√x", "SQRT"), ("yˣ", "YX"), ("LN", "LN"),
                              ("eˣ", "EXP"), ("n!", "FACT"), ("RND", "RND"), ("INTG", "INTG"), ("FRAC", "FRAC")]),
            ("Estatística", [("Σ-", "SIGMA_MINUS"), ("x̄,ȳ", "XBAR"), ("s", "SDEV"),
                              ("ŷ,r", "YHAT"), ("x̂,r", "XHAT"), ("x̄w", "XW")]),
            ("Financeiro (bonds/depreciação)", [("SL", "SL"), ("SOYD", "SOYD"), ("DB", "DB"),
                              ("PRICE", "BOND_PRICE"), ("YTM", "BOND_YTM")]),
            ("Calendário", [("ΔDYS", "DDYS"), ("D.MY", "DMY"), ("M.DY", "MDY")]),
            ("Programação", [("P/R", "PR_TOGGLE"), ("A", "LBL_A"), ("B", "LBL_B"), ("C", "LBL_C"),
                              ("D", "LBL_D"), ("E", "LBL_E"), ("x=0", "TEST0"), ("x:y", "TESTXY")]),
            ("Limpar", [("REG", "CLEAR_REG"), ("FIN", "CLEAR_FIN"), ("Σ", "CLEAR_SIGMA"), ("PRGM", "CLEAR_PRGM")]),
        ]
        row_i = 1
        for title, items in groups:
            tk.Label(panel, text=title, bg=EXT_BG, fg=EXT_LABEL_FG, font=("Segoe UI", 7)).grid(
                row=row_i, column=0, columnspan=4, sticky="w", pady=(6, 0))
            row_i += 1
            col = 0
            for label, action in items:
                btn = tk.Label(panel, text=label, bg=KEY_BG, fg=KEY_FG, font=("Segoe UI", 8),
                                width=6, height=1, relief="raised", bd=1, cursor="hand2")
                btn.grid(row=row_i, column=col, padx=1, pady=1)
                btn.bind("<ButtonPress-1>", lambda e, a=action: self.press(a))
                col += 1
                if col == 4:
                    col = 0
                    row_i += 1
            if col != 0:
                row_i += 1

    # ------------------------------------------------------------- input -
    def press(self, action: str) -> None:
        self.engine.press(action)
        self.refresh()

    def _on_key(self, event: tk.Event) -> None:
        ch = event.char
        keysym = event.keysym.lower()
        action = None
        if keysym == "return":
            action = "ENTER"
        elif keysym == "escape" or keysym == "backspace":
            action = "CLX"
        elif keysym == "f":
            action = "F"
        elif keysym == "g":
            action = "G"
        elif ch in KEYBOARD_MAP:
            action = KEYBOARD_MAP[ch]
        if action:
            self.press(action)
            if action in self.keys:
                self.keys[action].flash()

    def refresh(self) -> None:
        self._render_display()


def main() -> None:
    root = tk.Tk()
    App(root)
    root.mainloop()


if __name__ == "__main__":
    main()
