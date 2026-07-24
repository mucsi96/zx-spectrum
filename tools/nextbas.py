#!/usr/bin/env python3
"""
nextbas.py - convert between plain-text BASIC listings and the raw tokenized
.bas files used by the ZEsarUX NextBASIC host-disk patch (and by NextZXOS
itself: tokenized program body, no PLUS3DOS header).

    nextbas.py tokenize   listing.txt  program.bas
    nextbas.py detokenize program.bas  listing.txt

Covers classic Sinclair BASIC (the 48K token set), which is what NextBASIC
uses for these keywords. Numbers get their hidden 0x0E 5-byte binary form,
strings are kept verbatim, REM keeps the rest of the line untouched.
"""

import struct
import sys

# 48K Spectrum tokens 0xA5..0xFF
TOKENS = [
    "RND", "INKEY$", "PI", "FN", "POINT", "SCREEN$", "ATTR", "AT", "TAB",
    "VAL$", "CODE", "VAL", "LEN", "SIN", "COS", "TAN", "ASN", "ACS", "ATN",
    "LN", "EXP", "INT", "SQR", "SGN", "ABS", "PEEK", "IN", "USR", "STR$",
    "CHR$", "NOT", "BIN", "OR", "AND", "<=", ">=", "<>", "LINE", "THEN",
    "TO", "STEP", "DEF FN", "CAT", "FORMAT", "MOVE", "ERASE", "OPEN #",
    "CLOSE #", "MERGE", "VERIFY", "BEEP", "CIRCLE", "INK", "PAPER", "FLASH",
    "BRIGHT", "INVERSE", "OVER", "OUT", "LPRINT", "LLIST", "STOP", "READ",
    "DATA", "RESTORE", "NEW", "BORDER", "CONTINUE", "DIM", "REM", "FOR",
    "GO TO", "GO SUB", "INPUT", "LOAD", "LIST", "LET", "PAUSE", "NEXT",
    "POKE", "PRINT", "PLOT", "RUN", "SAVE", "RANDOMIZE", "IF", "CLS",
    "DRAW", "CLEAR", "RETURN", "COPY",
]
TOKEN_BASE = 0xA5
CODE_OF = {t: TOKEN_BASE + i for i, t in enumerate(TOKENS)}
# Accept the spaceless spellings too
CODE_OF["GOTO"] = CODE_OF["GO TO"]
CODE_OF["GOSUB"] = CODE_OF["GO SUB"]
CODE_OF["DEFFN"] = CODE_OF["DEF FN"]
# Longest first so e.g. "<=" wins over "<", "INPUT" over "IN"
MATCH_ORDER = sorted(CODE_OF, key=len, reverse=True)

REM_CODE = CODE_OF["REM"]
NUMBER_MARKER = 0x0E


def zx_float(value):
    """5-byte ZX Spectrum number representation."""
    if value == int(value) and 0 <= int(value) <= 65535:
        n = int(value)
        return bytes([0x00, 0x00, n & 0xFF, (n >> 8) & 0xFF, 0x00])
    # full floating point: value = mantissa * 2^(exp-128), 0.5 <= mantissa < 1
    m, e = value, 0
    while m >= 1.0:
        m /= 2.0
        e += 1
    while m < 0.5:
        m *= 2.0
        e -= 1
    mantissa = int(m * (1 << 32) + 0.5)
    if mantissa >= (1 << 32):  # rounding overflowed
        mantissa >>= 1
        e += 1
    b = struct.pack(">I", mantissa & 0x7FFFFFFF)  # top bit 0 = positive
    return bytes([(e + 128) & 0xFF]) + b


def is_word_char(c):
    return c.isalnum() or c == "$"


def tokenize_line(text):
    out = bytearray()
    i = 0
    n = len(text)
    while i < n:
        c = text[i]
        if c == '"':
            out.append(ord(c))
            i += 1
            while i < n:
                out.append(ord(text[i]))
                i += 1
                if text[i - 1] == '"':
                    break
            continue
        if c.isdigit() or (c == "." and i + 1 < n and text[i + 1].isdigit()):
            j = i
            while j < n and (text[j].isdigit() or text[j] == "."):
                j += 1
            if j < n and text[j] in "eE" and j + 1 < n and (
                text[j + 1].isdigit() or text[j + 1] in "+-"
            ):
                j += 2
                while j < n and text[j].isdigit():
                    j += 1
            literal = text[i:j]
            out.extend(literal.encode("ascii"))
            out.append(NUMBER_MARKER)
            out.extend(zx_float(float(literal)))
            i = j
            continue
        matched = None
        boundary = i == 0 or not is_word_char(text[i - 1])
        if boundary:
            for kw in MATCH_ORDER:
                if not text.startswith(kw, i):
                    continue
                end = i + len(kw)
                if kw[-1].isalnum() and end < n and is_word_char(text[end]):
                    continue  # inside a longer identifier
                matched = kw
                break
        if matched:
            out.append(CODE_OF[matched])
            i += len(matched)
            if i < n and text[i] == " ":
                i += 1  # LIST prints a space after keywords; don't store it
            if CODE_OF[matched] == REM_CODE:
                out.extend(text[i:].encode("latin-1"))
                i = n
            continue
        if c == " ":
            i += 1  # spacing is re-created by LIST
            continue
        out.append(ord(c) & 0xFF)
        i += 1
    return bytes(out)


def tokenize(source):
    body = bytearray()
    for raw in source.splitlines():
        line = raw.strip()
        if not line:
            continue
        k = 0
        while k < len(line) and line[k].isdigit():
            k += 1
        if k == 0:
            raise SystemExit(f"line without line number: {line!r}")
        number = int(line[:k])
        content = tokenize_line(line[k:].lstrip()) + b"\x0d"
        body += struct.pack(">H", number) + struct.pack("<H", len(content))
        body += content
    return bytes(body)


def detokenize(body):
    lines = []
    pos = 0
    while pos + 4 <= len(body):
        number = struct.unpack(">H", body[pos:pos + 2])[0]
        length = struct.unpack("<H", body[pos + 2:pos + 4])[0]
        content = body[pos + 4:pos + 4 + length]
        pos += 4 + length
        text = []
        i = 0
        while i < len(content):
            b = content[i]
            if b == NUMBER_MARKER:
                i += 6  # marker + 5-byte value; digits precede it
                continue
            if b == 0x0D:
                break
            if b >= TOKEN_BASE:
                kw = TOKENS[b - TOKEN_BASE]
                if text and text[-1] not in (" ", ""):
                    text.append(" ")
                text.append(kw)
                text.append(" ")
            else:
                text.append(chr(b))
            i += 1
        line = "".join(text)
        line = " ".join(line.split())  # normalize spacing
        lines.append(f"{number} {line}")
    return "\n".join(lines) + "\n"


def main():
    if len(sys.argv) != 4 or sys.argv[1] not in ("tokenize", "detokenize"):
        raise SystemExit(__doc__)
    mode, src, dst = sys.argv[1:]
    if mode == "tokenize":
        with open(src, "r", encoding="utf-8") as f:
            data = tokenize(f.read())
        with open(dst, "wb") as f:
            f.write(data)
    else:
        with open(src, "rb") as f:
            text = detokenize(f.read())
        with open(dst, "w", encoding="utf-8") as f:
            f.write(text)


if __name__ == "__main__":
    main()
