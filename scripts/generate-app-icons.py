#!/usr/bin/env python3
"""Regenerate HandForge GUI / tray PNG icons under handforge/resources/.

Requires Pillow: ``pip install Pillow``
"""

from __future__ import annotations

from pathlib import Path

try:
    from PIL import Image, ImageDraw
except ImportError as exc:  # pragma: no cover
    raise SystemExit("Pillow is required: pip install Pillow") from exc

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "handforge" / "resources"

BG = (28, 32, 40, 255)
RING = (232, 148, 48, 255)
WAVE = (255, 214, 140, 255)
ACCENT = (196, 98, 32, 255)


def make_icon(size: int) -> Image.Image:
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    m = max(1, size // 16)
    d.rounded_rectangle(
        [m, m, size - m - 1, size - m - 1], radius=size // 5, fill=BG
    )
    pad = size // 5
    d.ellipse(
        [pad, pad, size - pad - 1, size - pad - 1],
        outline=RING,
        width=max(2, size // 16),
    )
    cx, cy = size // 2, size // 2
    bars = 5
    bw = max(1, size // 14)
    gap = max(1, size // 20)
    heights = [0.35, 0.7, 1.0, 0.55, 0.4]
    total_w = bars * bw + (bars - 1) * gap
    x0 = cx - total_w // 2
    for i, h in enumerate(heights):
        bh = int(size * 0.28 * h)
        x = x0 + i * (bw + gap)
        y1 = cy - bh // 2
        y2 = cy + bh // 2
        color = WAVE if i == 2 else RING
        d.rounded_rectangle(
            [x, y1, x + bw, y2], radius=max(1, bw // 3), fill=color
        )
    base_y = size - pad - max(2, size // 24)
    d.rectangle(
        [
            pad + size // 8,
            base_y,
            size - pad - size // 8,
            base_y + max(2, size // 28),
        ],
        fill=ACCENT,
    )
    return img


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for size, name in (
        (16, "app_icon_16.png"),
        (32, "app_icon_32.png"),
        (64, "app_icon_64.png"),
        (128, "app_icon_128.png"),
        (256, "app_icon.png"),
    ):
        path = OUT / name
        make_icon(size).save(path, optimize=True)
        print(f"wrote {path.relative_to(ROOT)} ({path.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
