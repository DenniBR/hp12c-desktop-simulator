"""Generates an original app icon (not the HP logo, not any third-party asset):
a simple flat calculator glyph -- dark case, an LCD strip, a key grid -- in a
color scheme distinct from HP's own branding.
"""
from pathlib import Path

from PIL import Image, ImageDraw

OUT = Path(__file__).resolve().parent.parent / "assets" / "icon.ico"
SIZES = [16, 24, 32, 48, 64, 128, 256]


def draw(size: int) -> Image.Image:
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    m = size * 0.06
    body_color = (35, 41, 54, 255)      # slate navy, distinct from HP orange/black
    body_edge = (18, 21, 28, 255)
    lcd_color = (150, 214, 160, 255)    # green LCD tint
    key_color = (90, 150, 210, 255)     # soft blue keys

    r = size * 0.12
    d.rounded_rectangle([m, m, size - m, size - m], radius=r, fill=body_color, outline=body_edge, width=max(1, size // 64))

    lcd_pad = size * 0.16
    lcd_top = size * 0.16
    lcd_h = size * 0.20
    d.rounded_rectangle([lcd_pad, lcd_top, size - lcd_pad, lcd_top + lcd_h], radius=r * 0.4, fill=lcd_color)

    grid_top = lcd_top + lcd_h + size * 0.07
    grid_bottom = size - m - size * 0.06
    avail_h = grid_bottom - grid_top
    gap_ratio = 0.22
    cell = avail_h / (3 + 2 * gap_ratio)
    gap = cell * gap_ratio
    grid_w = 3 * cell + 2 * gap
    grid_left = (size - grid_w) / 2
    for row in range(3):
        for col in range(3):
            x0 = grid_left + col * (cell + gap)
            y0 = grid_top + row * (cell + gap)
            d.rounded_rectangle([x0, y0, x0 + cell, y0 + cell], radius=cell * 0.22, fill=key_color)
    return img


def main() -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    images = [draw(s) for s in SIZES]
    images[-1].save(OUT, format="ICO", sizes=[(s, s) for s in SIZES])
    print("wrote", OUT)


if __name__ == "__main__":
    main()
