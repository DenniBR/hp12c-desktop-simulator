"""Seven-segment style rendering for the LCD panel, drawn on a Tk Canvas.

Segment naming: a=top, b=upper-right, c=lower-right, d=bottom, e=lower-left,
f=upper-left, g=middle. A handful of letters (for "Error", "running", "Pr")
are approximated the way real 7-segment LCDs commonly render them.
"""
import tkinter as tk

SEGMENTS = {
    "0": "abcdef", "1": "bc", "2": "abged", "3": "abgcd", "4": "fgbc",
    "5": "afgcd", "6": "afgecd", "7": "abc", "8": "abcdefg", "9": "abcdfg",
    "-": "g", " ": "",
    "E": "afged", "R": "eg", "O": "gcde", "P": "abfge", "N": "ceg",
    "U": "fecd", "Y": "fgbcd", "L": "fed", "C": "afed", "T": "afg",
    "I": "", "G": "afedc",
}


def _segment_polygon(seg: str, w: float, h: float, t: float):
    half = h / 2
    if seg == "a":
        return [(t, 0), (w - t, 0), (w - t - t / 2, t), (t + t / 2, t)]
    if seg == "d":
        return [(t, h), (w - t, h), (w - t - t / 2, h - t), (t + t / 2, h - t)]
    if seg == "g":
        return [(t + t / 4, half), (w - t - t / 4, half),
                (w - t - t, half - t / 2), (t + t, half - t / 2)]
    if seg == "f":
        return [(0, t), (0, half - t / 4), (t, half - t / 2), (t, t + t / 2)]
    if seg == "b":
        return [(w, t), (w, half - t / 4), (w - t, half - t / 2), (w - t, t + t / 2)]
    if seg == "e":
        return [(0, half + t / 4), (0, h - t), (t, h - t - t / 2), (t, half + t / 2)]
    if seg == "c":
        return [(w, half + t / 4), (w, h - t), (w - t, h - t - t / 2), (w - t, half + t / 2)]
    raise ValueError(seg)


def draw_digit(canvas: tk.Canvas, x: float, y: float, w: float, h: float, ch: str,
                on_color: str, off_color: str, thickness: float = None, show_ghost: bool = True) -> None:
    t = thickness or w * 0.22
    lit = set(SEGMENTS.get(ch.upper(), ""))
    for seg in "abcdefg":
        color = on_color if seg in lit else (off_color if show_ghost else "")
        if not color:
            continue
        pts = _segment_polygon(seg, w, h, t)
        pts = [(px + x, py + y) for px, py in pts]
        canvas.create_polygon(pts, fill=color, outline="")


def measure(text: str, digit_w: float, gap: float) -> float:
    width = 0.0
    for ch in text:
        if ch == ".":
            width += digit_w * 0.35
        else:
            width += digit_w + gap
    return width


def draw_string(canvas: tk.Canvas, x: float, y: float, text: str, digit_w: float,
                 digit_h: float, gap: float, on_color: str, off_color: str,
                 show_ghost: bool = True) -> float:
    """Draws text left to right; '.' attaches as a dot after the previous
    digit rather than occupying its own cell. Returns total width used."""
    cursor = x
    for ch in text:
        if ch == ".":
            r = digit_w * 0.09
            cx = cursor - gap - r
            cy = y + digit_h - r
            canvas.create_oval(cx - r, cy - r, cx + r, cy + r, fill=on_color, outline="")
            cursor += digit_w * 0.35
            continue
        draw_digit(canvas, cursor, y, digit_w, digit_h, ch, on_color, off_color, show_ghost=show_ghost)
        cursor += digit_w + gap
    return cursor - x
