"""Tkinter desktop UI for the HP-12C Classic simulator.

Rebuilt from measured geometry, not from the previous widget tree. Every key
cell is a FIXED PIXEL SIZE frame (KEY_W x CELL_H) positioned with `.place()`,
not sized by Tkinter's character-unit Label width/height -- that's what let
the previous version drift toward a tall/square silhouette instead of the
reference photo's wide rectangle. Target overall body ratio ~1.55-1.65 (w:h),
matching the reference.

Structure (top to bottom): LCD row, then a 10-column x 4-row keypad on a
solid dark panel (financial row / math row / program row+tall ENTER /
f-g-STO-RCL row), with BOND/DEPRECIATION/CLEAR bracket labels between rows.
Nothing below that: the case ends where the keyboard panel ends, exactly as
in the reference. Engine actions with no physical key in the reference
(XBAR, SDEV, LBL_A-E, TEST0, TESTXY) are still in the engine and still
reachable programmatically -- they simply have no on-screen control, because
the reference calculator has none.

Every action string below is unchanged from the existing engine (see
engine.py's F_SHIFT/G_SHIFT for the routing table) -- this file only moves
WHERE a control sits and HOW it's drawn, never what it calls.
"""
import sys
import tkinter as tk
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from hp12c.engine import Engine  # noqa: E402
from ui import sevenseg  # noqa: E402

# ---------------------------------------------------------------- geometry --
# All pixel-measured from the user's reference file (600x375, hp12c.png):
# body ratio 560:357 = 1.57, LCD ~281x54, key pitch ~54px, keyboard panel
# occupies nearly the whole body height below the LCD, and the auxiliary
# strip is only ~15-18px tall in the original. KEY_H is picked (34, not the
# raw ~28px the pitch implies) specifically to hit that 1.57 body ratio once
# this app's own LCD block and window chrome are accounted for -- verified
# by screenshot, not assumed.
KEY_W = 64
KEY_H = 34
LABEL_H = 11         # gold/blue label strip height (px), each
CELL_H = LABEL_H + KEY_H + LABEL_H
GAP = 2              # px between adjacent keys
BRACKET_H = 14       # px for a BOND/DEPRECIATION/CLEAR bracket row
PANEL_PAD = 8        # px padding inside the dark keyboard panel
CASE_PAD = 12        # px cream margin around the whole instrument
# 2026-09-12 v1.0.1: LCD box re-measured directly off the reference photo --
# the previous 550x80 at centered position was NOT measured, it was a rough
# guess. Real pixel measurement (hp12c.png, full-res): the cream case at the
# LCD's row spans x=[20,579] (width 559), the glass spans x=[110,389]
# (width 280, height 55, rows 28-82) -- i.e. the glass is 50.1% of the case
# width, starts 16.1% of the case width from its left edge (NOT centered:
# 90px left margin vs 190px right margin), and its height is 9.84% of the
# case width. Scaled to this app's own case content width (696px, i.e.
# self.case's 720px minus its 2*CASE_PAD): glass width 348, glass height 69,
# left offset 112. The photo's LCD itself is powered off (flat glass, zero
# contrast variation even at 4x-boosted contrast) so no digit segment can be
# pixel-measured from it -- segment color/spacing below are a legibility
# correction, not a photo measurement, and are called out as such.
LCD_W, LCD_H = 348, 69
LCD_LEFT_OFFSET = 112

# ---------------------------------------------------------- colors (measured) -
CASE_BG = "#e6ddc6"        # cream body -- sampled (230,221,198)
CASE_BORDER = "#2a241a"
KEYBOARD_BG = "#373435"    # dark keyboard panel -- sampled (55,52,53)
KEY_BG = "#48484a"         # raised key face -- sampled (69-75,69-75,71-77)
KEY_FG = "#f4f1e8"
KEY_ACTIVE = "#65616a"
GOLD = "#e27e34"           # gold label text -- sampled (226,126,52)
BLUE = "#00aff0"           # blue label text -- sampled (0,175,240)
F_KEY_BG = "#e27b30"       # "f" key fill -- sampled (226,123,48)
G_KEY_BG = "#00aff0"       # "g" key fill -- sampled (0,175,240)
LCD_BG = "#979980"         # LCD glass -- sampled (151,153,128)
# 2026-09-12 v1.0.1: the reference photo's display is powered off (flat glass,
# no segments at any contrast boost -- see the LCD_W comment above), so these
# two colors are NOT a photo measurement. They are a legibility fix for the
# complaint that every segment read as "similar gray": LCD_ON is now much
# darker/near-black (real transmissive LCD segments read almost black against
# their glass, not mid-gray) and LCD_OFF sits much closer to LCD_BG itself
# (a bare ghost, not a second visible tone).
LCD_ON = "#12140d"
LCD_OFF = "#8b8e76"
MOLDING_BG = "#4b4b4d"     # bezel band between the cream case and the black
                           # panel -- sampled (75,75,77), distinct from both
PINSTRIPE = "#cbbfa0"      # thin cream accent line inset in that bezel -- sampled ~(205,195,165)


def _darken(hex_color: str, factor: float = 0.72) -> str:
    """Shades a key's face color for its blue-label sub-area -- the photo
    shows that area as a visibly darker tone of the same key, not a flat
    panel-colored gap."""
    r = int(hex_color[1:3], 16)
    g = int(hex_color[3:5], 16)
    b = int(hex_color[5:7], 16)
    return f"#{int(r * factor):02x}{int(g * factor):02x}{int(b * factor):02x}"

KEYBOARD_MAP = {
    "0": "D0", "1": "D1", "2": "D2", "3": "D3", "4": "D4", "5": "D5",
    "6": "D6", "7": "D7", "8": "D8", "9": "D9", ".": "DOT",
    "+": "ADD", "-": "SUB", "*": "MUL", "/": "DIV",
    "\r": "ENTER", "\x1b": "CLX", "\x08": "CLX",
}


class Key(tk.Frame):
    """One fixed-pixel-size keycap (KEY_W x CELL_H, or x(2*CELL_H+GAP) when
    `tall=True` for ENTER): gold label above on the panel, then the key body
    itself -- which the photo shows as ONE bordered cap split into two
    physical areas, a larger main-label region on top and a smaller, visibly
    DARKER blue-label region on the bottom (separated by a 1px reveal of the
    panel color, not just two labels floating on the panel). `action=None`
    makes the key inert (used only for the decorative ON key)."""

    SUB_H = 12  # px, the blue-label sub-area's fixed height within the face

    def __init__(self, master, engine_callback, label, action, gold=None, blue=None, tall=False,
                 face_bg=None, face_fg=None):
        h = CELL_H if not tall else CELL_H * 2 + GAP
        super().__init__(master, width=KEY_W, height=h, bg=KEYBOARD_BG)
        self.pack_propagate(False)
        self.action = action
        self.callback = engine_callback
        self.face_bg = face_bg or KEY_BG
        self.sub_bg = _darken(self.face_bg)

        tk.Label(self, text=gold or "", bg=KEYBOARD_BG, fg=GOLD,
                  font=("Segoe UI", 6)).place(x=0, y=0, width=KEY_W, height=LABEL_H)

        face_h = h - 2 * LABEL_H
        sub_h = self.SUB_H
        main_h = face_h - sub_h - 1  # 1px reveal of KEYBOARD_BG = the seam between the two areas

        self.btn = tk.Label(self, text=label, bg=self.face_bg, fg=face_fg or KEY_FG,
                             font=("Segoe UI", 9, "bold"), relief="raised", bd=2,
                             cursor="hand2", anchor="n" if tall else "center")
        self.btn.place(x=0, y=LABEL_H, width=KEY_W, height=main_h)

        self.sub = tk.Label(self, text=blue or "", bg=self.sub_bg, fg=BLUE,
                             font=("Segoe UI", 7, "bold"), relief="raised", bd=1,
                             cursor="hand2")
        self.sub.place(x=0, y=LABEL_H + main_h + 1, width=KEY_W, height=sub_h)

        for widget in (self.btn, self.sub):
            widget.bind("<ButtonPress-1>", self._press)
            widget.bind("<ButtonRelease-1>", self._release)

    def _press(self, _event=None):
        self.btn.configure(relief="sunken", bg=KEY_ACTIVE)
        if self.action is not None:
            self.callback(self.action)

    def _release(self, _event=None):
        self.btn.configure(relief="raised", bg=self.face_bg)

    def flash(self):
        self.btn.configure(relief="sunken", bg=KEY_ACTIVE)
        self.after(90, lambda: self.btn.configure(relief="raised", bg=self.face_bg))


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

        self.case = tk.Frame(root, bg=CASE_BG, padx=CASE_PAD, pady=CASE_PAD)
        self.case.pack()

        self._build_display(self.case)
        self._build_core_keypad(self.case)

        root.bind("<Key>", self._on_key)
        self.refresh()

    # ---------------------------------------------------------- display --
    def _build_display(self, parent) -> None:
        frame = tk.Frame(parent, bg=CASE_BG)
        frame.pack(fill="x", pady=(0, 8))
        # Measured off-centre: the reference's glass sits 112px from the
        # case's left edge with 236px of cream to its right, not centered.
        self.canvas = tk.Canvas(frame, width=LCD_W, height=LCD_H, bg=LCD_BG,
                                 highlightthickness=2, highlightbackground="#4a4636")
        self.canvas.pack(anchor="w", padx=(LCD_LEFT_OFFSET, 0))
        self.annunciators = tk.Label(frame, text="", bg=CASE_BG, fg=GOLD, font=("Segoe UI", 8, "bold"))
        self.annunciators.pack(anchor="w", padx=(LCD_LEFT_OFFSET, 0))

    def _render_display(self) -> None:
        self.canvas.delete("all")
        text = self.engine.display_text()
        # Digit box re-tuned to the resized LCD: height is ~68% of the glass
        # (real LCD digits nearly fill the display band), width:height ~0.51
        # (matches common 7-segment calculator digit proportions), and the
        # inter-digit gap is cut from 25% to 12% of digit width -- the old
        # 5px gap on a 20px digit read as loose "separate drawings", not one
        # number.
        digit_w, digit_h, gap = 24, 47, 3
        total_w = sevenseg.measure(text, digit_w, gap)
        x = max(6, LCD_W - 10 - total_w)
        sevenseg.draw_string(self.canvas, x, (LCD_H - digit_h) // 2, text, digit_w, digit_h, gap, LCD_ON, LCD_OFF)

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
        """10 columns x 4 rows on a solid dark panel, matching the reference
        photo: financial row, math row, program row (ENTER spans this row
        and the next), f/g/STO/RCL row, with BOND/DEPRECIATION/CLEAR bracket
        labels between rows. All gold/blue sub-labels shown here (including
        MEM, PSE, BST, x<=y, x=0) are transcribed directly from the measured
        reference photo. PSE/BST/x<=y/x=0 are printed on the caps but carry no
        g-shift routing in this build -- shown as engraving, not as a promise
        of behaviour."""
        # Cream case -> molding band -> pinstripe accent -> black panel: the
        # photo never goes straight from cream to black, it has this bezel
        # sandwich in between (measured: an ~8px gray band, then a ~2px
        # cream pinstripe, both sampled directly from the reference file).
        molding = tk.Frame(parent, bg=MOLDING_BG)
        molding.pack()
        pinstripe = tk.Frame(molding, bg=PINSTRIPE)
        pinstripe.pack(padx=8, pady=8)
        panel = tk.Frame(pinstripe, bg=KEYBOARD_BG, padx=PANEL_PAD, pady=PANEL_PAD)
        panel.pack(padx=2, pady=2)
        grid = tk.Frame(panel, bg=KEYBOARD_BG)
        grid.pack()

        rows = [
            [("n", "N", "AMORT", "12x"), ("i", "I", "INT", "12/"), ("PV", "PV", "NPV", "CFo"),
             ("PMT", "PMT", "RND", "CFj"), ("FV", "FV", "IRR", "Nj"), ("CHS", "CHS", None, "DATE"),
             ("7", "D7", None, "BEG"), ("8", "D8", None, "END"), ("9", "D9", None, "MEM"),
             ("÷", "DIV", None, None)],
            [("yˣ", "YX", "PRICE", "√x"), ("1/x", "INV", "YTM", "eˣ"), ("%T", "PCT_TOTAL", "SL", "LN"),
             ("Δ%", "DELTA_PCT", "SOYD", "FRAC"), ("%", "PCT", "DB", "INTG"), ("EEX", "EEX", None, "ΔDYS"),
             ("4", "D4", None, "D.MY"), ("5", "D5", None, "M.DY"), ("6", "D6", None, "x̄w"),
             ("×", "MUL", None, None)],
            # Row3col2/col3 corrected against the measured reference photo:
            # the real primary keys are SST (not implemented -> honest no-op)
            # and R-down (RDOWN, already implemented) -- see engine.py's
            # F_SHIFT/G_SHIFT for "Sigma"/"PRGM"/"GTO" now routed correctly.
            # Blue sub-labels PSE/BST/x<=y/x=0 are shown as measured from the
            # reference photo but carry no g-shift action (engine unchanged).
            [("R/S", "RS", "P/R", "PSE"), ("SST", "SST", "Σ", "BST"),
             ("R↓", "RDOWN", "PRGM", "GTO"), ("x≷y", "XY", "FIN", "x≤y"), ("CLx", "CLX", "REG", "x=0"),
             ("ENTER", "ENTER", "PREFIX", "LSTx"),
             ("1", "D1", None, "x̂,r"), ("2", "D2", None, "ŷ,r"), ("3", "D3", None, "n!"),
             ("−", "SUB", None, None)],
            [("ON", None, None, None), ("f", "F", None, None), ("g", "G", None, None),
             ("STO", "STO", None, None), ("RCL", "RCL", None, None),
             # column 5 (ENTER) already rendered tall in the row above, skipped here
             ("0", "D0", None, "x̄"), (".", "DOT", None, "s"), ("Σ+", "SIGMA_PLUS", None, "Σ-"),
             ("+", "ADD", None, None)],
        ]
        # Logical row -> grid row, leaving a thin bracket row above rows 2
        # and 3 (none needed above row 1 or between rows 3-4).
        grid_row_of = {0: 0, 1: 2, 2: 4, 3: 5}
        self._bracket(grid, row=1, col=0, span=2, text="BOND")
        self._bracket(grid, row=1, col=2, span=3, text="DEPRECIATION")
        self._bracket(grid, row=3, col=1, span=4, text="CLEAR")

        # "f" and "g" have colored faces on the real keyboard (measured:
        # #E27B30 orange, #00AFF0 blue) -- not plain grey like every other key.
        face_colors = {"F": (F_KEY_BG, "#3a2000"), "G": (G_KEY_BG, "#00263a")}

        self.keys = {}
        for r, row in enumerate(rows):
            grid_row = grid_row_of[r]
            c = 0
            for label, action, gold, blue in row:
                if r == 3 and c == 5:
                    c += 1  # ENTER's column: occupied by the tall key from the row above
                face_bg, face_fg = face_colors.get(action, (None, None))
                if action == "ENTER":
                    key = Key(grid, self.press, label, action, gold, blue, tall=True)
                    key.grid(row=grid_row, column=c, rowspan=2, padx=GAP // 2, pady=GAP // 2)
                else:
                    key = Key(grid, self.press, label, action, gold, blue,
                               face_bg=face_bg, face_fg=face_fg)
                    key.grid(row=grid_row, column=c, padx=GAP // 2, pady=GAP // 2)
                self.keys[action] = key
                c += 1

    @staticmethod
    def _bracket(grid: tk.Frame, row: int, col: int, span: int, text: str) -> None:
        """A real bracket, not a loose label over a line: a horizontal gold
        rule with a short downward tick at each end (the photo's group
        markings look like an open-topped bracket cupping the keys below),
        the group name sitting on top of the rule with the rule broken
        behind it (a same-color label background over the line's midpoint)."""
        width = span * (KEY_W + GAP) - GAP
        holder = tk.Frame(grid, bg=KEYBOARD_BG, width=width, height=BRACKET_H)
        holder.grid(row=row, column=col, columnspan=span, sticky="ew")
        holder.grid_propagate(False)

        line_y = 5
        tick_h = 6
        tick_w = 2
        tk.Frame(holder, bg=GOLD).place(x=tick_w, y=line_y, width=width - 2 * tick_w, height=1)
        tk.Frame(holder, bg=GOLD).place(x=0, y=line_y, width=tick_w, height=tick_h)
        tk.Frame(holder, bg=GOLD).place(x=width - tick_w, y=line_y, width=tick_w, height=tick_h)
        tk.Label(holder, text=text, bg=KEYBOARD_BG, fg=GOLD,
                 font=("Segoe UI", 6, "bold")).place(relx=0.5, y=line_y, anchor="center")

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
