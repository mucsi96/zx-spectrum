"""Sinclair BASIC keyword catalog of the rubber-key 48K ZX Spectrum.

Every named keyword token printed on the keyboard in white (keyword mode), green
(extended mode) and red (symbol shift / extended-symbol shift). Only the bare
comparison glyphs (<=, >=, <>) and pure punctuation symbols are left out, since
they are not named commands and do not work as a picture.

The generator does NOT print a card for every keyword here. It scans the BASIC
programs in the repository's programs/ folder and makes cards only for the
keywords actually used there — this catalog is what it recognises keywords
against. (Use --all to print the whole catalog.)

Just the keyword names are listed — the image-prompt model (GPT 5.6) already
knows what each Sinclair BASIC command does, so no descriptions are needed.
The order below is roughly how approachable each command is for a young
beginner; cards are printed in this order.
"""

KEYWORDS = [
    # everyday commands
    "PRINT", "LET", "INPUT", "RUN", "LIST", "CLS", "NEW", "GOTO", "GOSUB",
    "RETURN", "IF", "THEN", "FOR", "TO", "STEP", "NEXT", "PAUSE", "STOP",
    "REM", "BORDER", "PAPER", "INK", "FLASH", "BRIGHT", "INVERSE", "OVER",
    "BEEP", "CLEAR", "CONTINUE", "COPY", "LOAD", "SAVE",
    # graphics, data, sequences, printer, files and common functions
    "PLOT", "DRAW", "CIRCLE", "POKE", "PEEK", "DIM", "DATA", "READ",
    "RESTORE", "RANDOMIZE", "AT", "TAB", "LINE", "LPRINT", "LLIST", "LEN",
    "STR$", "VAL", "VAL$", "CHR$", "CODE", "RND", "INKEY$", "AND", "OR",
    "NOT", "DEF FN", "FN", "MERGE", "VERIFY", "CAT", "FORMAT", "MOVE",
    "ERASE", "OPEN #", "CLOSE #", "IN", "OUT",
    # maths and machine-level functions
    "SIN", "COS", "TAN", "ASN", "ACS", "ATN", "LN", "EXP", "INT", "SQR",
    "SGN", "ABS", "PI", "USR", "BIN", "POINT", "SCREEN$", "ATTR",
]
