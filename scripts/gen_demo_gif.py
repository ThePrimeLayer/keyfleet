"""Regenerate docs/demo.gif — a type-on recording of real keyfleet output.

Usage:
    uv run --with pillow python scripts/gen_demo_gif.py [--inspect DIR]

Pillow is deliberately not a project dependency; the committed GIF is the
artifact. The script drives the real CLI in-process against
scripts/demo_ledger.yaml, so the demo can never drift from actual behavior.
``--inspect DIR`` additionally writes each scene's final frame as PNG.

Font: tries Consolas / Menlo / DejaVu Sans Mono; override with
KEYFLEET_DEMO_FONT=/path/to/mono.ttf.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
from typer.testing import CliRunner

from keyfleet.cli import app

ROOT = Path(__file__).resolve().parent.parent
LEDGER = str(Path(__file__).resolve().parent / "demo_ledger.yaml")
OUT = ROOT / "docs" / "demo.gif"

BG = (13, 17, 23)
BAR_BG = (22, 27, 34)
FG = (230, 237, 243)
BRIGHT = (255, 255, 255)
DIM = (139, 148, 158)
RED = (248, 81, 73)
YELLOW = (210, 153, 34)
CYAN = (88, 166, 255)
GREEN = (63, 185, 80)

FONT_SIZE = 16
LINE_H = 24
PAD = 16
BAR = 34
MIN_WIDTH = 900

FONT_CANDIDATES = (
    os.environ.get("KEYFLEET_DEMO_FONT"),
    r"C:\Windows\Fonts\consola.ttf",
    "/System/Library/Fonts/Menlo.ttc",
    "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
)

Seg = tuple[str, tuple[int, int, int]]


def load_font() -> ImageFont.FreeTypeFont:
    for candidate in FONT_CANDIDATES:
        if candidate and Path(candidate).exists():
            return ImageFont.truetype(candidate, FONT_SIZE)
    raise SystemExit("no monospace font found — set KEYFLEET_DEMO_FONT=/path/to/mono.ttf")


def capture(*args: str) -> list[str]:
    result = CliRunner().invoke(app, list(args))
    return result.output.rstrip("\n").splitlines()


def style_check_line(line: str) -> list[Seg]:
    for prefix, color in (("FAIL", RED), ("WARN", YELLOW), ("INFO", CYAN)):
        if line.startswith(prefix):
            return [(prefix, color), (line[len(prefix) :], FG)]
    if line.startswith("keyfleet"):
        return [(line, BRIGHT)]
    return [(line, FG)]


def style_lost_line(line: str) -> list[Seg]:
    if line.startswith("keyfleet"):
        return [(line, BRIGHT)]
    if line.lstrip().startswith(("de-register:", "settings:")):
        label, _, rest = line.partition(":")
        return [(label + ":", DIM), (rest, FG)]
    for token, color in (("INACCESSIBLE", RED), ("below policy", YELLOW), ("OK", GREEN)):
        if token in line:
            before, after = line.split(token, 1)
            return [(before, FG), (token, color), (after, FG)]
    return [(line, FG)]


def prompt_line(command: str) -> list[Seg]:
    return [("$ ", GREEN), (command, BRIGHT)]


def render(
    lines: list[list[Seg]], height_lines: int, font: ImageFont.FreeTypeFont, width: int
) -> Image.Image:
    image = Image.new("RGB", (width, BAR + PAD * 2 + height_lines * LINE_H), BG)
    draw = ImageDraw.Draw(image)
    draw.rectangle([0, 0, width, BAR], fill=BAR_BG)
    for i, color in enumerate(((255, 95, 86), (255, 189, 46), (39, 201, 63))):
        draw.ellipse([14 + i * 22, BAR // 2 - 6, 26 + i * 22, BAR // 2 + 6], fill=color)
    title = "keyfleet — demo"
    draw.text(
        ((width - font.getlength(title)) // 2, BAR // 2 - FONT_SIZE // 2 - 1),
        title,
        font=font,
        fill=DIM,
    )
    y = BAR + PAD
    for segments in lines:
        x = float(PAD)
        for text, color in segments:
            draw.text((x, y), text, font=font, fill=color)
            x += font.getlength(text)
        y += LINE_H
    return image


def main() -> None:
    font = load_font()
    check_lines = [style_check_line(line) for line in capture("check", LEDGER)]
    lost_lines = [style_lost_line(line) for line in capture("lost", "yk-old", LEDGER)]
    height_lines = max(len(check_lines), len(lost_lines)) + 1  # + prompt line
    longest = max(
        font.getlength("".join(text for text, _ in segments))
        for segments in (*check_lines, *lost_lines)
    )
    width = max(MIN_WIDTH, int(longest) + 2 * PAD + 4)

    frames: list[Image.Image] = []
    durations: list[int] = []

    def emit(lines: list[list[Seg]], milliseconds: int) -> None:
        frames.append(render(lines, height_lines, font, width))
        durations.append(milliseconds)

    def type_on(command: str) -> None:
        for i in range(2, len(command) + 1, 2):
            emit([prompt_line(command[:i])], 70)
        emit([prompt_line(command)], 400)

    type_on("keyfleet check")
    emit([prompt_line("keyfleet check"), *check_lines[:1]], 250)
    scene_check = [prompt_line("keyfleet check"), *check_lines]
    emit(scene_check, 3800)

    type_on("keyfleet lost yk-old")
    scene_lost = [prompt_line("keyfleet lost yk-old"), *lost_lines]
    emit(scene_lost, 5500)

    OUT.parent.mkdir(exist_ok=True)
    frames[0].save(
        OUT,
        save_all=True,
        append_images=frames[1:],
        duration=durations,
        loop=0,
        optimize=True,
    )
    print(f"wrote {OUT} ({OUT.stat().st_size / 1024:.0f} KiB, {len(frames)} frames)")

    if "--inspect" in sys.argv:
        inspect_dir = Path(sys.argv[sys.argv.index("--inspect") + 1])
        inspect_dir.mkdir(parents=True, exist_ok=True)
        render(scene_check, height_lines, font, width).save(inspect_dir / "scene_check.png")
        render(scene_lost, height_lines, font, width).save(inspect_dir / "scene_lost.png")
        print(f"inspection frames in {inspect_dir}")


if __name__ == "__main__":
    main()
