# Sinclair BASIC memory cards

Generates a printable **PDF of memory-game cards** that teach a young child (≈7)
the Sinclair BASIC commands of the rubber-key ZX Spectrum.

Each command becomes a **matching pair**:

- a **word card** — the BASIC keyword (`PRINT`, `BEEP`, `CIRCLE`, …) with a short,
  child-friendly description, and
- a **picture card** — an AI-drawn pictogram of what the command does.

The child wins a pair by matching the keyword to the right picture.

## How the pictures are made (two AI steps per command)

1. **Claude Opus** is asked, one command at a time, to invent a short
   *image-generation prompt* describing a clear pictogram for that command.
2. **OpenAI's image model** turns that prompt into a PNG.

Both results are cached under `cache/` (prompts in `cache/prompts.json`, images in
`cache/images/`), so re-running only does the work that is missing and you never
pay for the same picture twice.

## Groups

Commands are split into three decks, so you can start easy and add harder cards later:

| Deck | Colour | Commands |
|------|--------|----------|
| **Simple** (used every session) | green | `PRINT` `LET` `INPUT` `RUN` `LIST` `CLS` `GOTO` `NEW` |
| **Intermediate** (loops, sound, colour) | orange | `IF` `FOR` `GOSUB` `BEEP` `PAUSE` `BORDER` `PAPER` `INK` |
| **Advanced** (graphics, memory, data) | purple | `PLOT` `DRAW` `CIRCLE` `POKE` `PEEK` `DATA` `DIM` `RANDOMIZE` |

Each deck is 8 commands = 16 cards = exactly **one A4 page** (a 4×4 grid).
Every card carries the deck's colour and a matching corner dot, so after cutting you
can keep the Simple deck separate and play with just those first.

## Usage

```bash
cd sinclair-memory-cards
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

export ANTHROPIC_API_KEY=sk-ant-...
export OPENAI_API_KEY=sk-...

# Preview the layout with no AI calls / no cost:
python generate_cards.py --placeholder

# Generate the real cards (all three decks):
python generate_cards.py

# Just the easy deck:
python generate_cards.py --groups simple

# Rebuild the PDF from the cache without calling any AI again:
python generate_cards.py --skip-generation
```

The result is `sinclair-memory-cards.pdf`. Print it at **100% / actual size**
(turn off "fit to page"), then cut along the rounded card borders. Card size is
about 44 × 66 mm — a comfortable size for small hands. Printing on thin card or
gluing to cardboard makes the cards last longer and stops the picture showing
through from behind.

## Model overrides (optional)

| Variable | Default | Notes |
|----------|---------|-------|
| `CLAUDE_MODEL` | `claude-opus-4-5` | Any Claude Opus model id (the latest Opus is a good choice). |
| `OPENAI_IMAGE_MODEL` | `gpt-image-1` | Set to whichever OpenAI image model you have access to. |

## Files

- `generate_cards.py` — the generator (AI calls + PDF layout)
- `commands.py` — the command list, descriptions and deck colours (edit to taste)
- `requirements.txt` — Python dependencies
- `cache/` — generated prompts and images (safe to delete to regenerate)
