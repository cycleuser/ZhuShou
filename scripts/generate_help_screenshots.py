#!/usr/bin/env python3
"""
Generate CLI help screenshots for ZhuShou documentation.

Produces:
  images/zhushou_help.txt  -- Plain text capture (always)
  images/zhushou_help.png  -- PNG image with terminal styling (needs Pillow)

Usage:
    python3 scripts/generate_help_screenshots.py
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

# ── Configuration ────────────────────────────────────────────────────────────

PROJECT_ROOT = Path(__file__).resolve().parent.parent
IMAGES_DIR = PROJECT_ROOT / "images"
TOOL_NAME = "zhushou"

# PNG rendering parameters (per spec section 五)
BG_COLOR = (30, 30, 30)        # Deep grey background
FG_COLOR = (204, 204, 204)     # Light grey text
TITLE_BG = (50, 50, 50)        # Slightly lighter grey for title bar
FONT_SIZE = 14
PADDING = 16
TITLE_HEIGHT = 32
TERMINAL_WIDTH = 80


def capture_help_text() -> str:
    """Run ``zhushou --help`` and return the stdout text."""
    env = os.environ.copy()
    env["COLUMNS"] = str(TERMINAL_WIDTH)

    result = subprocess.run(
        [sys.executable, "-m", TOOL_NAME, "--help"],
        capture_output=True,
        text=True,
        timeout=15,
        env=env,
    )
    if result.returncode != 0:
        print(f"Warning: --help exited with code {result.returncode}", file=sys.stderr)
        if result.stderr:
            print(result.stderr, file=sys.stderr)

    return result.stdout.strip()


def save_txt(text: str, path: Path) -> None:
    """Write the plain text capture."""
    path.write_text(text + "\n", encoding="utf-8")
    print(f"  Saved: {path.relative_to(PROJECT_ROOT)}")


def save_png(text: str, path: Path) -> None:
    """Render *text* as a terminal-style PNG image."""
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        print("  Skipping PNG: Pillow not installed (pip install Pillow)")
        return

    # Try to find a monospace font
    font = None
    font_candidates = [
        "DejaVuSansMono.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
        "/usr/share/fonts/TTF/DejaVuSansMono.ttf",
        "/System/Library/Fonts/Menlo.ttc",
        "/System/Library/Fonts/Monaco.dfont",
        "C:\\Windows\\Fonts\\consola.ttf",
        "C:\\Windows\\Fonts\\lucon.ttf",
    ]
    for candidate in font_candidates:
        try:
            font = ImageFont.truetype(candidate, FONT_SIZE)
            break
        except (OSError, IOError):
            continue

    if font is None:
        try:
            font = ImageFont.truetype("DejaVuSansMono", FONT_SIZE)
        except (OSError, IOError):
            font = ImageFont.load_default()
            print("  Warning: Using default font (monospace not found)")

    # Measure text dimensions
    lines = text.split("\n")
    dummy_img = Image.new("RGB", (1, 1))
    draw = ImageDraw.Draw(dummy_img)

    # Measure max line width and line height
    max_width = 0
    line_height = 0
    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font)
        w = bbox[2] - bbox[0]
        h = bbox[3] - bbox[1]
        if w > max_width:
            max_width = w
        if h > line_height:
            line_height = h

    line_height = max(line_height, FONT_SIZE + 4)

    img_width = max_width + PADDING * 2
    img_height = TITLE_HEIGHT + len(lines) * line_height + PADDING * 2

    # Create image
    img = Image.new("RGB", (img_width, img_height), BG_COLOR)
    draw = ImageDraw.Draw(img)

    # Draw title bar
    draw.rectangle(
        [(0, 0), (img_width, TITLE_HEIGHT)],
        fill=TITLE_BG,
    )
    title_text = f"$ {TOOL_NAME} --help"
    draw.text(
        (PADDING, (TITLE_HEIGHT - FONT_SIZE) // 2),
        title_text,
        fill=FG_COLOR,
        font=font,
    )

    # Draw text lines
    y = TITLE_HEIGHT + PADDING
    for line in lines:
        draw.text((PADDING, y), line, fill=FG_COLOR, font=font)
        y += line_height

    img.save(str(path))
    print(f"  Saved: {path.relative_to(PROJECT_ROOT)}")


def main() -> int:
    print(f"Generating CLI help screenshots for {TOOL_NAME}...\n")

    IMAGES_DIR.mkdir(exist_ok=True)

    # Capture help text
    print("  Capturing --help output...")
    help_text = capture_help_text()

    if not help_text:
        print("  Error: No help output captured!", file=sys.stderr)
        return 1

    # Save .txt (always)
    txt_path = IMAGES_DIR / f"{TOOL_NAME}_help.txt"
    save_txt(help_text, txt_path)

    # Save .png (needs Pillow)
    png_path = IMAGES_DIR / f"{TOOL_NAME}_help.png"
    save_png(help_text, png_path)

    print(f"\nDone! Screenshots are in {IMAGES_DIR.relative_to(PROJECT_ROOT)}/")
    return 0


if __name__ == "__main__":
    sys.exit(main())
