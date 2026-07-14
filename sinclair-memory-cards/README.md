# Sinclair BASIC memory cards

Generates a printable **PDF of memory-game cards** that teach a young child (≈7)
the Sinclair BASIC commands of the rubber-key ZX Spectrum.

The card set is driven by the programs we actually write: the script scans the
BASIC programs in the repository's [`programs/`](../programs) folder, extracts the
unique Sinclair BASIC keywords used in them, and makes cards **only for those** —
so the learning starts with the commands that really come up, not the whole
keyboard at random. Add a new program and re-run: cards for its newly-used
commands are added (everything already generated is cached).

Each command becomes a **matching pair**:

- a **word card** — just the BASIC keyword (`PRINT`, `BEEP`, `CIRCLE`, …), big and clear, and
- a **picture card** — an AI-drawn pictogram of what the command does.

The child wins a pair by matching the keyword to the right picture. There is no
other text to read: the cards are plain **square, black-on-white** cards, and the
only colour anywhere is inside the pictures. The pictures are **white-background
vector-graphic art** in one consistent style across the whole deck.

## How the pictures are made (two AI steps per command)

1. **GPT 5.5** is asked, one command at a time, to invent a short
   *image-generation prompt* describing a clear pictogram for that command
   (it already knows what each Sinclair BASIC command does).
2. **Ideogram 4 Turbo** turns that prompt into a PNG.

Both results are cached under `cache/` (prompts in `cache/prompts.json`, images in
`cache/images/`), so re-running only does the work that is missing and you never
pay for the same picture twice.

## Which commands get cards

By default: **the keywords used in `programs/*.bas`**. The scanner understands
real Spectrum listings — it ignores line numbers, text inside `"strings"` and
`REM` comments, and recognises `GO TO` / `GO SUB` (as the keyboard spells them)
as `GOTO` / `GOSUB`.

Recognition happens against the full catalog in `commands.py` — every named
keyword printed on the rubber-key keyboard in **white** (keyword mode), **green**
(extended mode) and **red** (symbol shift); only the bare comparison glyphs
`<=` `>=` `<>` and pure punctuation are left out, as they aren't named commands.
Pass `--all` to print the entire catalog instead of scanning the programs.

Found commands are split into three decks so the easy ones can be played alone:

| Deck | Corner mark | Contains (when used in a program) |
|------|-------------|-----------------------------------|
| **Simple** — typed every session, plus colour & sound | 1 dot | `PRINT` `LET` `INPUT` `RUN` `LIST` `CLS` `NEW` `GOTO` `GOSUB` `RETURN` `IF` `THEN` `FOR` `TO` `STEP` `NEXT` `PAUSE` `STOP` `REM` `BORDER` `PAPER` `INK` `FLASH` `BRIGHT` `INVERSE` `OVER` `BEEP` `CLEAR` `CONTINUE` `COPY` `LOAD` `SAVE` |
| **Intermediate** — graphics, data, printer, files, common functions | 2 dots | `PLOT` `DRAW` `CIRCLE` `POKE` `PEEK` `DIM` `DATA` `READ` `RESTORE` `RANDOMIZE` `AT` `TAB` `LINE` `LPRINT` `LLIST` `LEN` `STR$` `VAL` `VAL$` `CHR$` `CODE` `RND` `INKEY$` `AND` `OR` `NOT` `DEF FN` `FN` `MERGE` `VERIFY` `CAT` `FORMAT` `MOVE` `ERASE` `OPEN #` `CLOSE #` `IN` `OUT` |
| **Advanced** — maths & machine functions | 3 dots | `SIN` `COS` `TAN` `ASN` `ACS` `ATN` `LN` `EXP` `INT` `SQR` `SGN` `ABS` `PI` `USR` `BIN` `POINT` `SCREEN$` `ATTR` |

Each deck flows across as many A4 pages as it needs (20 cards to a page, in a 4×5
grid of squares). The only marking of the deck is one, two or three **small faint dots** in the
top-right corner — deliberately unobtrusive, just enough to sort the cards back into
decks after cutting so you can play with the Simple deck on its own first.

> One GPT 5.5 call + one Ideogram call per command, both cached — so you only ever
> pay for a command's picture once, no matter how many times you re-run.

## Setting up the environment

### Nix flakes (recommended)

The `flake.nix` here provides a pinned Python (currently 3.12 — set via
`pythonAttr` at the top of the flake) that already has the dependencies — no
virtualenv, no `pip install`. It reads the package list straight from
`requirements.txt`, so the dependencies are only ever listed in one place.

```bash
cd sinclair-memory-cards
nix develop            # drops you into a shell with the right Python
```

If you use [direnv](https://direnv.net), an `.envrc` is included — run
`direnv allow` once and the shell loads automatically whenever you `cd` in.

### Plain pip (alternative)

```bash
cd sinclair-memory-cards
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

## Secrets (`.env`)

Copy `.env.example` to `.env` and fill in your keys:

```bash
cp .env.example .env
$EDITOR .env        # set OPENAI_API_KEY and IDEOGRAM_API_KEY
```

The generator loads `.env` automatically (no `python-dotenv` needed). The real
`.env` is git-ignored — never commit it. If a variable is already exported in
your shell, that value wins over the file.

## Generating the cards

Once you're in the environment (Nix shell or venv) and have your `.env`:

```bash
# Preview the layout with no AI calls / no cost:
python generate_cards.py --placeholder

# Generate cards for the commands used in ../programs (the default):
python generate_cards.py

# Just the easy deck:
python generate_cards.py --groups simple

# The full keyboard catalog instead of scanning the programs:
python generate_cards.py --all

# Scan a different folder of .bas files:
python generate_cards.py --programs /path/to/programs

# Rebuild the PDF from the cache without calling any AI again:
python generate_cards.py --skip-generation
```

The result is `sinclair-memory-cards.pdf`. Print it at **100% / actual size**
(turn off "fit to page"), then cut along the square card borders. Cards are about
44 × 44 mm squares — a comfortable size for small hands. Printing on thin card or
gluing to cardboard makes the cards last longer and stops the picture showing
through from behind.

## Model overrides (optional)

| Variable | Default | Notes |
|----------|---------|-------|
| `OPENAI_TEXT_MODEL` | `gpt-5.5` | The OpenAI model used to write each image prompt. |
| `IDEOGRAM_URL` | `https://api.ideogram.ai/v1/ideogram-v4/generate` | Ideogram generate endpoint. |
| `IDEOGRAM_RENDERING_SPEED` | `TURBO` | `TURBO`, `DEFAULT` or `QUALITY`. |
| `IDEOGRAM_ASPECT_RATIO` | `1x1` | Square by default; set empty to let the model choose. |

## Files

- `generate_cards.py` — the generator (program scanning + AI calls + PDF layout)
- `commands.py` — the keyword catalog and deck definitions (edit to taste)
- `flake.nix` — Nix dev shell; reads its package list from `requirements.txt`
- `.env.example` — template for your API keys; copy to `.env` (git-ignored)
- `.envrc` — optional direnv hook to auto-load the Nix shell
- `requirements.txt` — the one dependency list, used by both pip and the flake
- `cache/` — generated prompts and images (safe to delete to regenerate)
