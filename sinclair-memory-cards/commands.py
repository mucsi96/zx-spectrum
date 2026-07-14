"""Sinclair BASIC keywords of the rubber-key 48K ZX Spectrum, grouped by difficulty.

This is the *catalog* of every named keyword token printed on the keyboard in white
(keyword mode), green (extended mode) and red (symbol shift / extended-symbol shift).
Only the bare comparison glyphs (<=, >=, <>) and pure punctuation symbols are left
out, since they are not named commands and do not work as a picture.

The generator does NOT print a card for every keyword here. It scans the BASIC
programs in the repository's programs/ folder and makes cards only for the keywords
actually used there — this catalog is what it recognises keywords against, and what
assigns each found keyword to a deck. (Use --all to print the whole catalog.)

Just the keyword names are listed — the image-prompt model (GPT 5.5) already knows
what each Sinclair BASIC command does, so no descriptions are needed.

Deck grouping is by how useful/approachable a command is for a young beginner:
  simple       - the commands you type every session, plus colour and sound
  intermediate - graphics, data, sequences, the printer, files and common functions
  advanced     - the maths and machine-level functions (rarely needed by a beginner)
"""

COMMANDS = {
    "simple": [
        "PRINT", "LET", "INPUT", "RUN", "LIST", "CLS", "NEW", "GOTO", "GOSUB",
        "RETURN", "IF", "THEN", "FOR", "TO", "STEP", "NEXT", "PAUSE", "STOP",
        "REM", "BORDER", "PAPER", "INK", "FLASH", "BRIGHT", "INVERSE", "OVER",
        "BEEP", "CLEAR", "CONTINUE", "COPY", "LOAD", "SAVE",
    ],
    "intermediate": [
        "PLOT", "DRAW", "CIRCLE", "POKE", "PEEK", "DIM", "DATA", "READ",
        "RESTORE", "RANDOMIZE", "AT", "TAB", "LINE", "LPRINT", "LLIST", "LEN",
        "STR$", "VAL", "VAL$", "CHR$", "CODE", "RND", "INKEY$", "AND", "OR",
        "NOT", "DEF FN", "FN", "MERGE", "VERIFY", "CAT", "FORMAT", "MOVE",
        "ERASE", "OPEN #", "CLOSE #", "IN", "OUT",
    ],
    "advanced": [
        "SIN", "COS", "TAN", "ASN", "ACS", "ATN", "LN", "EXP", "INT", "SQR",
        "SGN", "ABS", "PI", "USR", "BIN", "POINT", "SCREEN$", "ATTR",
    ],
}

# Per-group display info. No colours on the cards themselves (colour is only ever
# used inside the AI pictures). Decks are told apart by a number of small faint dots
# ("rank"), so a deck can still be sorted out after the cards are cut.
GROUP_STYLE = {
    "simple":       {"label": "Simple",       "rank": 1},
    "intermediate": {"label": "Intermediate", "rank": 2},
    "advanced":     {"label": "Advanced",     "rank": 3},
}

GROUP_ORDER = ["simple", "intermediate", "advanced"]
