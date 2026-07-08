#!/usr/bin/env python3
"""Generate a printable PDF of memory-game cards for Sinclair BASIC commands.

For every command you get a *pair* of cards:
  * a "word" card with the BASIC keyword and a child-friendly description
  * a "picture" card with an AI-drawn pictogram of what the command does

The picture for each command is produced in two AI steps, as requested:
  1. Claude Opus is asked to invent a short image-generation prompt describing a
     clear pictogram for that one command (one Claude call per command).
  2. OpenAI's image model turns that prompt into a PNG (one image call per command).

Both steps are cached on disk, so re-running only does the work that is missing.
The cards are laid out 16 to an A4 page (4x4) with each group on its own page(s),
so you can play with just the Simple deck first, then add the harder ones.

Usage:
    export ANTHROPIC_API_KEY=sk-ant-...
    export OPENAI_API_KEY=sk-...
    python generate_cards.py                      # all three groups
    python generate_cards.py --groups simple      # just the easy deck
    python generate_cards.py --placeholder         # no API calls: preview the layout
    python generate_cards.py --skip-generation     # rebuild the PDF from the cache only

Model overrides (optional):
    CLAUDE_MODEL         (default: claude-opus-4-5)   any Claude Opus model id
    OPENAI_IMAGE_MODEL   (default: gpt-image-1)       OpenAI image model id
"""
from __future__ import annotations

import argparse
import base64
import json
import os
import re
import sys
from pathlib import Path

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.colors import HexColor, Color
from reportlab.pdfgen import canvas
from reportlab.pdfbase.pdfmetrics import stringWidth

from commands import COMMANDS, GROUP_STYLE, GROUP_ORDER

HERE = Path(__file__).resolve().parent
CACHE_DIR = HERE / "cache"
IMAGES_DIR = CACHE_DIR / "images"
PROMPTS_FILE = CACHE_DIR / "prompts.json"

CLAUDE_MODEL = os.environ.get("CLAUDE_MODEL", "claude-opus-4-5")
OPENAI_IMAGE_MODEL = os.environ.get("OPENAI_IMAGE_MODEL", "gpt-image-1")

# Appended to every image prompt so the whole deck shares one look.
STYLE_SUFFIX = (
    " Flat, colourful children's picture-book cartoon style, bold simple shapes, "
    "thick clean outlines, bright friendly colours, one clear centred subject, "
    "plain white background, plenty of empty margin, no text, no letters, no numbers, "
    "no words anywhere in the image."
)

CLAUDE_SYSTEM = (
    "You design pictograms for a memory-matching card game that teaches a 7-year-old "
    "child the commands of Sinclair BASIC on the rubber-key ZX Spectrum. "
    "For the single command you are given, invent ONE clear, literal picture that a "
    "child could look at and instantly connect to what the command does. "
    "It must be a concrete visual scene or object, not an abstract idea, and it must "
    "not rely on any text, letters or numbers being drawn. "
    "Reply with ONLY the image-generation prompt: one or two vivid sentences describing "
    "exactly what should be drawn. Do not add explanations, quotes or a preamble."
)


def slugify(cmd: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", cmd.lower()).strip("-")


# --------------------------------------------------------------------------- #
# AI step 1: Claude Opus invents the image prompt.
# --------------------------------------------------------------------------- #
def get_image_prompt(client, info: dict) -> str:
    user = (
        f"Sinclair BASIC command: {info['cmd']}\n"
        f"What it does: {info['does']}\n"
        f"Child-friendly hint: {info['desc']}"
    )
    resp = client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=500,
        system=CLAUDE_SYSTEM,
        messages=[{"role": "user", "content": user}],
    )
    return "".join(b.text for b in resp.content if b.type == "text").strip()


# --------------------------------------------------------------------------- #
# AI step 2: OpenAI turns the prompt into a PNG.
# --------------------------------------------------------------------------- #
def generate_image(client, prompt: str, out_path: Path) -> None:
    result = client.images.generate(
        model=OPENAI_IMAGE_MODEL,
        prompt=prompt + STYLE_SUFFIX,
        size="1024x1024",
        n=1,
    )
    data = result.data[0]
    if getattr(data, "b64_json", None):
        img_bytes = base64.b64decode(data.b64_json)
    elif getattr(data, "url", None):
        import urllib.request
        with urllib.request.urlopen(data.url) as r:
            img_bytes = r.read()
    else:
        raise RuntimeError("Image API returned neither b64_json nor url")
    out_path.write_bytes(img_bytes)


def load_prompts() -> dict:
    if PROMPTS_FILE.exists():
        return json.loads(PROMPTS_FILE.read_text())
    return {}


def save_prompts(prompts: dict) -> None:
    PROMPTS_FILE.write_text(json.dumps(prompts, indent=2, ensure_ascii=False))


def generate_assets(groups: list[str]) -> dict:
    """Run the two AI steps for every command in the selected groups (cached)."""
    import anthropic
    import openai

    if not os.environ.get("ANTHROPIC_API_KEY"):
        sys.exit("ANTHROPIC_API_KEY is not set (or use --placeholder to preview the layout).")
    if not os.environ.get("OPENAI_API_KEY"):
        sys.exit("OPENAI_API_KEY is not set (or use --placeholder to preview the layout).")

    claude = anthropic.Anthropic()
    oai = openai.OpenAI()

    prompts = load_prompts()
    for group in groups:
        for info in COMMANDS[group]:
            slug = slugify(info["cmd"])
            if slug not in prompts:
                print(f"  [Claude] prompt for {info['cmd']} ...")
                prompts[slug] = get_image_prompt(claude, info)
                save_prompts(prompts)  # persist after each success
            img_path = IMAGES_DIR / f"{slug}.png"
            if not img_path.exists():
                print(f"  [OpenAI] image for {info['cmd']} ...")
                generate_image(oai, prompts[slug], img_path)
    return prompts


# --------------------------------------------------------------------------- #
# PDF layout.
# --------------------------------------------------------------------------- #
PAGE_W, PAGE_H = A4
MARGIN = 10 * mm
GUTTER = 4 * mm
COLS, ROWS = 4, 4
PER_PAGE = COLS * ROWS
CARD_W = (PAGE_W - 2 * MARGIN - (COLS - 1) * GUTTER) / COLS
CARD_H = (PAGE_H - 2 * MARGIN - (ROWS - 1) * GUTTER) / ROWS
RADIUS = 3 * mm


def _fit_font(text: str, font: str, max_w: float, start: float, min_size: float = 8) -> float:
    size = start
    while size > min_size and stringWidth(text, font, size) > max_w:
        size -= 1
    return size


def _wrap(text: str, font: str, size: float, max_w: float) -> list[str]:
    words, lines, cur = text.split(), [], ""
    for w in words:
        trial = f"{cur} {w}".strip()
        if stringWidth(trial, font, size) <= max_w:
            cur = trial
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def _corner_dot(c: canvas.Canvas, x: float, y: float, border: Color) -> None:
    c.setFillColor(border)
    c.setStrokeColor(border)
    c.circle(x + CARD_W - 5 * mm, y + CARD_H - 5 * mm, 2 * mm, stroke=0, fill=1)


def draw_card_frame(c: canvas.Canvas, x: float, y: float, style: dict, fill: bool) -> None:
    border = HexColor(style["border"])
    c.setLineWidth(1.6)
    c.setStrokeColor(border)
    c.setFillColor(HexColor(style["fill"]) if fill else HexColor("#FFFFFF"))
    c.roundRect(x, y, CARD_W, CARD_H, RADIUS, stroke=1, fill=1)
    # small group label, top-left
    c.setFillColor(border)
    c.setFont("Helvetica-Bold", 6)
    c.drawString(x + 4 * mm, y + CARD_H - 6.5 * mm, style["label"].upper())
    _corner_dot(c, x, y, border)


def draw_word_card(c: canvas.Canvas, x: float, y: float, info: dict, style: dict) -> None:
    draw_card_frame(c, x, y, style, fill=True)
    border = HexColor(style["border"])
    inner_w = CARD_W - 8 * mm

    keyword = info["cmd"]
    size = _fit_font(keyword, "Helvetica-Bold", inner_w, 30)
    c.setFillColor(border)
    c.setFont("Helvetica-Bold", size)
    c.drawCentredString(x + CARD_W / 2, y + CARD_H * 0.58, keyword)

    c.setFillColor(HexColor("#333333"))
    lines = _wrap(info["desc"], "Helvetica", 9, inner_w)
    ty = y + CARD_H * 0.40
    c.setFont("Helvetica", 9)
    for line in lines:
        c.drawCentredString(x + CARD_W / 2, ty, line)
        ty -= 4.6 * mm


def draw_picture_card(c: canvas.Canvas, x: float, y: float, info: dict, style: dict,
                      img_path: Path | None) -> None:
    draw_card_frame(c, x, y, style, fill=False)
    pad = 6 * mm
    box_x, box_y = x + pad, y + pad
    box_w, box_h = CARD_W - 2 * pad, CARD_H - 2 * pad - 4 * mm
    if img_path and img_path.exists():
        c.drawImage(str(img_path), box_x, box_y, box_w, box_h,
                    preserveAspectRatio=True, anchor="c", mask="auto")
    else:
        # placeholder so you can preview the layout without any API calls
        c.setStrokeColor(HexColor("#BBBBBB"))
        c.setFillColor(HexColor("#FAFAFA"))
        c.setDash(2, 2)
        c.roundRect(box_x, box_y, box_w, box_h, 2 * mm, stroke=1, fill=1)
        c.setDash()
        c.setFillColor(HexColor("#999999"))
        c.setFont("Helvetica-Oblique", 8)
        c.drawCentredString(x + CARD_W / 2, y + CARD_H / 2 + 2 * mm, "picture of")
        c.setFont("Helvetica-Bold", 11)
        c.drawCentredString(x + CARD_W / 2, y + CARD_H / 2 - 4 * mm, info["cmd"])


def build_pdf(groups: list[str], output: Path) -> None:
    c = canvas.Canvas(str(output), pagesize=A4)
    for group in groups:
        style = GROUP_STYLE[group]
        cards = []  # (kind, info)
        for info in COMMANDS[group]:
            cards.append(("word", info))
        for info in COMMANDS[group]:
            cards.append(("pic", info))

        for page_start in range(0, len(cards), PER_PAGE):
            page_cards = cards[page_start:page_start + PER_PAGE]
            for i, (kind, info) in enumerate(page_cards):
                col = i % COLS
                row = i // COLS
                x = MARGIN + col * (CARD_W + GUTTER)
                y = PAGE_H - MARGIN - CARD_H - row * (CARD_H + GUTTER)
                if kind == "word":
                    draw_word_card(c, x, y, info, style)
                else:
                    img_path = IMAGES_DIR / f"{slugify(info['cmd'])}.png"
                    draw_picture_card(c, x, y, info, style, img_path)
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

    # keep the group order stable regardless of argument order
    groups = [g for g in GROUP_ORDER if g in args.groups]

    CACHE_DIR.mkdir(exist_ok=True)
    IMAGES_DIR.mkdir(exist_ok=True)

    if not (args.placeholder or args.skip_generation):
        print("Generating pictograms (Claude prompt -> OpenAI image, cached):")
        generate_assets(groups)

    print(f"Building PDF: {args.output}")
    build_pdf(groups, args.output)
    print("Done. Print at 100% / actual size (no 'fit to page') and cut along the card borders.")


if __name__ == "__main__":
    main()
