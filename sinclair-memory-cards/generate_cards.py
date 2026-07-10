#!/usr/bin/env python3
"""Generate a printable PDF of memory-game cards for Sinclair BASIC commands.

For every command you get a *pair* of cards:
  * a "word" card with just the BASIC keyword
  * a "picture" card with an AI-drawn pictogram of what the command does

The picture for each command is produced in two AI steps:
  1. GPT 5.5 is asked to invent a short image-generation prompt describing a clear
     pictogram for that one command (it already knows what each command does).
  2. Ideogram 4 Turbo turns that prompt into a PNG.

Both steps are cached on disk, so re-running only does the work that is missing.
The cards are laid out 20 to an A4 page (4x5 squares); each deck flows across as
many pages as it needs, so you can play with just the Simple deck first.

Usage:
    cp .env.example .env      # then put your OPENAI_API_KEY / IDEOGRAM_API_KEY in it
    python generate_cards.py                      # all three groups
    python generate_cards.py --groups simple      # just the easy deck
    python generate_cards.py --placeholder         # no API calls: preview the layout
    python generate_cards.py --skip-generation     # rebuild the PDF from the cache only

Keys are read from a local .env file (or the real environment, which takes
precedence).

Model / endpoint overrides (optional):
    OPENAI_TEXT_MODEL         (default: gpt-5.5)
    IDEOGRAM_URL              (default: https://api.ideogram.ai/v1/ideogram-v4/generate)
    IDEOGRAM_RENDERING_SPEED  (default: TURBO)   TURBO | DEFAULT | QUALITY
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.colors import HexColor
from reportlab.pdfgen import canvas
from reportlab.pdfbase.pdfmetrics import stringWidth

from commands import COMMANDS, GROUP_STYLE, GROUP_ORDER

HERE = Path(__file__).resolve().parent
CACHE_DIR = HERE / "cache"
IMAGES_DIR = CACHE_DIR / "images"
PROMPTS_FILE = CACHE_DIR / "prompts.json"

OPENAI_TEXT_MODEL = os.environ.get("OPENAI_TEXT_MODEL", "gpt-5.5")
IDEOGRAM_URL = os.environ.get(
    "IDEOGRAM_URL", "https://api.ideogram.ai/v1/ideogram-v4/generate")
IDEOGRAM_RENDERING_SPEED = os.environ.get("IDEOGRAM_RENDERING_SPEED", "TURBO")

# Appended to every image prompt so the whole deck shares one look.
STYLE_SUFFIX = (
    " Vector graphic art: clean flat vector illustration, bold geometric shapes, "
    "crisp smooth outlines, bright flat colour fills, no gradients, no shading, "
    "no photographic texture, one clear friendly centred subject, "
    "pure solid white background, generous empty margin, "
    "no text, no letters, no numbers, no words anywhere in the image."
)

PROMPT_SYSTEM = (
    "You design pictograms for a memory-matching card game that teaches a 7-year-old "
    "child the commands of Sinclair BASIC on the rubber-key ZX Spectrum. "
    "You will be given one Sinclair BASIC keyword. Recall what that command does, then "
    "invent ONE clear, literal picture that a child could look at and instantly connect "
    "to what the command does. It must be a concrete visual scene or object, not an "
    "abstract idea, and it must not rely on any text, letters or numbers being drawn. "
    "Reply with ONLY the image-generation prompt: one or two vivid sentences describing "
    "exactly what should be drawn. Do not add explanations, quotes or a preamble."
)


def slugify(cmd: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", cmd.lower()).strip("-")


def load_dotenv(path: Path) -> None:
    """Load KEY=VALUE lines from a .env file into the environment.

    Deliberately tiny (no python-dotenv dependency). Real environment variables
    always win — values from the file only fill in what is not already set.
    """
    if not path.exists():
        return
    for raw in path.read_text().splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[len("export "):].lstrip()
        key, sep, val = line.partition("=")
        if not sep:
            continue
        key, val = key.strip(), val.strip()
        if len(val) >= 2 and val[0] == val[-1] and val[0] in "\"'":
            val = val[1:-1]
        if key:
            os.environ.setdefault(key, val)


# --------------------------------------------------------------------------- #
# AI step 1: GPT 5.5 invents the image prompt.
# --------------------------------------------------------------------------- #
def get_image_prompt(client, cmd: str) -> str:
    resp = client.chat.completions.create(
        model=OPENAI_TEXT_MODEL,
        messages=[
            {"role": "system", "content": PROMPT_SYSTEM},
            {"role": "user", "content": f"Sinclair BASIC keyword: {cmd}"},
        ],
    )
    return (resp.choices[0].message.content or "").strip()


# --------------------------------------------------------------------------- #
# AI step 2: Ideogram 4 Turbo turns the prompt into a PNG.
# --------------------------------------------------------------------------- #
def generate_image(prompt: str, out_path: Path, api_key: str) -> None:
    import requests

    # Ideogram v3/v4 generate endpoints take multipart/form-data; passing text
    # fields via `files` (value tuple with a None filename) makes requests send
    # multipart rather than urlencoded.
    fields = {
        "prompt": (None, prompt + STYLE_SUFFIX),
        "rendering_speed": (None, IDEOGRAM_RENDERING_SPEED),
        "aspect_ratio": (None, "1x1"),
        "num_images": (None, "1"),
        "magic_prompt": (None, "OFF"),
    }
    resp = requests.post(
        IDEOGRAM_URL, headers={"Api-Key": api_key}, files=fields, timeout=180)
    resp.raise_for_status()
    url = resp.json()["data"][0]["url"]
    # Ideogram image URLs are ephemeral — download the bytes right away.
    img = requests.get(url, timeout=180)
    img.raise_for_status()
    out_path.write_bytes(img.content)


def load_prompts() -> dict:
    if PROMPTS_FILE.exists():
        return json.loads(PROMPTS_FILE.read_text())
    return {}


def save_prompts(prompts: dict) -> None:
    PROMPTS_FILE.write_text(json.dumps(prompts, indent=2, ensure_ascii=False))


def generate_assets(groups: list[str]) -> dict:
    """Run the two AI steps for every command in the selected groups (cached)."""
    import openai

    if not os.environ.get("OPENAI_API_KEY"):
        sys.exit("OPENAI_API_KEY is not set (or use --placeholder to preview the layout).")
    ideogram_key = os.environ.get("IDEOGRAM_API_KEY")
    if not ideogram_key:
        sys.exit("IDEOGRAM_API_KEY is not set (or use --placeholder to preview the layout).")

    oai = openai.OpenAI()

    prompts = load_prompts()
    for group in groups:
        for cmd in COMMANDS[group]:
            slug = slugify(cmd)
            if slug not in prompts:
                print(f"  [GPT 5.5] prompt for {cmd} ...")
                prompts[slug] = get_image_prompt(oai, cmd)
                save_prompts(prompts)  # persist after each success
            img_path = IMAGES_DIR / f"{slug}.png"
            if not img_path.exists():
                print(f"  [Ideogram] image for {cmd} ...")
                generate_image(prompts[slug], img_path, ideogram_key)
    return prompts


# --------------------------------------------------------------------------- #
# PDF layout.
# --------------------------------------------------------------------------- #
PAGE_W, PAGE_H = A4
MARGIN = 10 * mm
GUTTER = 4 * mm
COLS = 4
# Square cards, so more rows fit down the page than the old tall cards.
CARD = (PAGE_W - 2 * MARGIN - (COLS - 1) * GUTTER) / COLS
ROWS = int((PAGE_H - 2 * MARGIN + GUTTER) // (CARD + GUTTER))
PER_PAGE = COLS * ROWS

# The cards themselves are black on white only — colour lives solely in the pictures.
INK = HexColor("#000000")


def _fit_font(text: str, font: str, max_w: float, start: float, min_size: float = 8) -> float:
    size = start
    while size > min_size and stringWidth(text, font, size) > max_w:
        size -= 1
    return size


def _deck_marks(c: canvas.Canvas, x: float, y: float, rank: int) -> None:
    """Small, faint dots in the top-right corner mark the deck without shouting:
    1 dot = Simple, 2 = Intermediate, 3 = Advanced. Only used for sorting cut cards."""
    r, gap = 0.9 * mm, 1.5 * mm
    c.setFillColor(HexColor("#B0B0B0"))
    for i in range(rank):
        cx = x + CARD - 3.5 * mm - i * gap
        c.circle(cx, y + CARD - 3.5 * mm, r, stroke=0, fill=1)


def draw_card_frame(c: canvas.Canvas, x: float, y: float, style: dict) -> None:
    c.setLineWidth(1.2)
    c.setStrokeColor(INK)
    c.setFillColor(HexColor("#FFFFFF"))
    c.rect(x, y, CARD, CARD, stroke=1, fill=1)  # square, sharp corners
    _deck_marks(c, x, y, style["rank"])


def draw_word_card(c: canvas.Canvas, x: float, y: float, cmd: str, style: dict) -> None:
    """Just the command keyword, big and centred. Nothing else to read."""
    draw_card_frame(c, x, y, style)
    size = _fit_font(cmd, "Helvetica-Bold", CARD - 7 * mm, 34)
    c.setFillColor(INK)
    c.setFont("Helvetica-Bold", size)
    c.drawCentredString(x + CARD / 2, y + CARD / 2 - size * 0.34, cmd)


def draw_picture_card(c: canvas.Canvas, x: float, y: float, cmd: str, style: dict,
                      img_path: Path | None) -> None:
    """Just the picture, filling the card."""
    draw_card_frame(c, x, y, style)
    pad = 3.5 * mm
    box_x, box_y = x + pad, y + pad
    box = CARD - 2 * pad
    if img_path and img_path.exists():
        c.drawImage(str(img_path), box_x, box_y, box, box,
                    preserveAspectRatio=True, anchor="c", mask="auto")
    else:
        # placeholder so you can preview the layout without any API calls
        c.setStrokeColor(HexColor("#BBBBBB"))
        c.setFillColor(HexColor("#FAFAFA"))
        c.setDash(2, 2)
        c.rect(box_x, box_y, box, box, stroke=1, fill=1)
        c.setDash()
        c.setFillColor(HexColor("#999999"))
        c.setFont("Helvetica-Oblique", 7)
        c.drawCentredString(x + CARD / 2, y + CARD / 2 + 1 * mm, "picture of")
        c.setFont("Helvetica-Bold", 10)
        c.drawCentredString(x + CARD / 2, y + CARD / 2 - 4 * mm, cmd)


def build_pdf(groups: list[str], output: Path) -> None:
    c = canvas.Canvas(str(output), pagesize=A4)
    for group in groups:
        style = GROUP_STYLE[group]
        cards = [("word", cmd) for cmd in COMMANDS[group]]
        cards += [("pic", cmd) for cmd in COMMANDS[group]]

        for page_start in range(0, len(cards), PER_PAGE):
            page_cards = cards[page_start:page_start + PER_PAGE]
            for i, (kind, cmd) in enumerate(page_cards):
                col = i % COLS
                row = i // COLS
                x = MARGIN + col * (CARD + GUTTER)
                y = PAGE_H - MARGIN - CARD - row * (CARD + GUTTER)
                if kind == "word":
                    draw_word_card(c, x, y, cmd, style)
                else:
                    img_path = IMAGES_DIR / f"{slugify(cmd)}.png"
                    draw_picture_card(c, x, y, cmd, style, img_path)
            c.showPage()
    c.save()


# --------------------------------------------------------------------------- #
def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--groups", nargs="+", choices=GROUP_ORDER, default=GROUP_ORDER,
                    help="which difficulty groups to include (default: all)")
    ap.add_argument("--output", type=Path, default=HERE / "sinclair-memory-cards.pdf",
                    help="output PDF path")
    ap.add_argument("--placeholder", action="store_true",
                    help="skip all AI calls and draw placeholder pictures (layout preview)")
    ap.add_argument("--skip-generation", action="store_true",
                    help="do not call any AI; build the PDF from whatever is already cached")
    args = ap.parse_args()

    # Pick up OPENAI_API_KEY / IDEOGRAM_API_KEY from a local .env if present.
    load_dotenv(HERE / ".env")

    # keep the group order stable regardless of argument order
    groups = [g for g in GROUP_ORDER if g in args.groups]

    CACHE_DIR.mkdir(exist_ok=True)
    IMAGES_DIR.mkdir(exist_ok=True)

    if not (args.placeholder or args.skip_generation):
        print("Generating pictograms (GPT 5.5 prompt -> Ideogram 4 Turbo image, cached):")
        generate_assets(groups)

    print(f"Building PDF: {args.output}")
    build_pdf(groups, args.output)
    print("Done. Print at 100% / actual size (no 'fit to page') and cut along the card borders.")


if __name__ == "__main__":
    main()
