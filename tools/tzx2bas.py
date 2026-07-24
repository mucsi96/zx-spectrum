#!/usr/bin/env python3
"""
tzx2bas.py - convert BASIC programs saved by the old Fuse 48K setup into the
plain-text .bas listings used by the ZX Spectrum Next kiosk.

Reads .tzx and .tap tape files (e.g. ~/tapes/*.tzx written by the Fuse
savehook patch, or an accumulated tape.tzx), finds every BASIC program on
them (header block type 0 + data block) and writes one listing per program:

    tools/tzx2bas.py ~/tapes -o ~/programs
    tools/tzx2bas.py game.tzx other.tap -o programs/

The listings use exactly the conventions of the emulator patch, so they
LOAD straight into NextBASIC: keywords expanded like LIST, hidden number
bytes dropped, block graphics as Unicode quadrant characters (empty block
80h as \\..), UDGs as \\a..\\u, pound/copyright as UTF-8, anything else as
a lossless \\xHH escape. The variables area (beyond the header's "start of
variables" offset) is dropped, like the kiosk's own SAVE.

Existing output files are never overwritten unless --force is given.
CODE/array blocks are skipped with a note. Only Python 3 stdlib needed.
"""

import argparse
import pathlib
import sys

# 48K Spectrum tokens 0xA5..0xFF; 0xA3/0xA4 are the 128K extras
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
TOKENS_128 = {0xA3: "SPECTRUM", 0xA4: "PLAY"}
REM_CODE = 0xEA
NUMBER_MARKER = 0x0E

# Unicode quadrant characters for block graphics 0x81..0x8F
# (bit 0 = top right, bit 1 = top left, bit 2 = bottom right, bit 3 = bottom left)
BLOCKS = {
    1: "▝", 2: "▘", 3: "▀", 4: "▗", 5: "▐", 6: "▚", 7: "▜",
    8: "▖", 9: "▞", 10: "▌", 11: "▛", 12: "▄", 13: "▟", 14: "▙", 15: "█",
}


def emit_zx_char(b):
    """Host text representation of one ZX character inside a string/REM."""
    if b == 0x60:
        return "£"
    if b == 0x7F:
        return "©"
    if b == 0x5C:
        return "\\\\"
    if b == 0x80:
        return "\\.."
    if 0x81 <= b <= 0x8F:
        return BLOCKS[b - 0x80]
    if 0x90 <= b <= 0xA4:
        return "\\" + chr(ord("a") + b - 0x90)
    if 32 <= b < 127:
        return chr(b)
    return f"\\x{b:02X}"


def detokenize(body, warnings):
    """Tokenized BASIC program -> listing text (same rules as the patch)."""
    lines = []
    pos = 0
    while pos + 4 <= len(body):
        number = (body[pos] << 8) | body[pos + 1]
        length = body[pos + 2] | (body[pos + 3] << 8)
        end = min(pos + 4 + length, len(body))
        pos += 4
        if number > 9999:
            warnings.append(f"stopped at bad line number {number} (corrupt tail?)")
            break
        out = [f"{number} "]
        in_string = in_rem = False
        while pos < end:
            b = body[pos]
            if b == 0x0D:
                pos += 1
                break
            if not in_string and not in_rem and b == NUMBER_MARKER:
                pos += 6  # digits precede; drop the hidden binary form
                continue
            if not in_rem and b == 0x22:
                in_string = not in_string
            if not in_string and not in_rem and b >= 0xA3:
                keyword = TOKENS_128.get(b) or TOKENS[b - TOKEN_BASE]
                if b in TOKENS_128:
                    warnings.append(
                        f"line {number}: 128K keyword {keyword} - the kiosk "
                        "tokenizer will not re-tokenize it"
                    )
                if out[-1] and not out[-1].endswith(" "):
                    out.append(" ")
                out.append(keyword + " ")
                if b == REM_CODE:
                    in_rem = True
            else:
                out.append(emit_zx_char(b))
            pos += 1
        lines.append("".join(out).rstrip())
    return "\n".join(lines) + "\n"


def tap_blocks(data):
    """Yields raw tape blocks (flag byte...checksum) from a .tap file."""
    pos = 0
    while pos + 2 <= len(data):
        length = data[pos] | (data[pos + 1] << 8)
        pos += 2
        yield data[pos:pos + length]
        pos += length


def tzx_blocks(data, warnings):
    """Yields raw tape blocks from a .tzx file, skipping non-data blocks."""
    if data[:8] != b"ZXTape!\x1a":
        raise ValueError("not a TZX file")
    pos = 10
    while pos < len(data):
        block_id = data[pos]
        pos += 1

        def word(off):
            return data[pos + off] | (data[pos + off + 1] << 8)

        if block_id == 0x10:  # standard speed data
            length = word(2)
            yield data[pos + 4:pos + 4 + length]
            pos += 4 + length
        elif block_id == 0x11:  # turbo speed data
            length = word(0x0F) | (data[pos + 0x11] << 16)
            yield data[pos + 0x12:pos + 0x12 + length]
            pos += 0x12 + length
        elif block_id == 0x12:
            pos += 4
        elif block_id == 0x13:
            pos += 1 + 2 * data[pos]
        elif block_id == 0x14:  # pure data
            length = word(7) | (data[pos + 9] << 16)
            yield data[pos + 0x0A:pos + 0x0A + length]
            pos += 0x0A + length
        elif block_id == 0x20:
            pos += 2
        elif block_id == 0x21:
            pos += 1 + data[pos]
        elif block_id == 0x22:
            pos += 0
        elif block_id == 0x30:
            pos += 1 + data[pos]
        elif block_id == 0x31:
            pos += 2 + data[pos + 1]
        elif block_id == 0x32:
            pos += 2 + word(0)
        elif block_id == 0x33:
            pos += 1 + 3 * data[pos]
        elif block_id == 0x35:
            pos += 0x10 + 4 + (word(0x10) | (word(0x12) << 16))
        elif block_id == 0x5A:
            pos += 9
        else:
            warnings.append(f"unknown TZX block 0x{block_id:02X}, stopping scan")
            return


def sanitize(name):
    cleaned = "".join(
        c if c.isalnum() or c in "_- " else "_" for c in name
    ).strip()
    return cleaned or "untitled"


def extract_programs(blocks, warnings):
    """Yields (name, program_bytes, autostart) for each BASIC program."""
    header = None
    for block in blocks:
        if len(block) < 2:
            continue
        flag = block[0]
        payload = block[1:-1]  # strip flag and checksum
        checksum = 0
        for b in block:
            checksum ^= b
        if checksum != 0:
            warnings.append("tape block with bad checksum (converted anyway)")
            payload = block[1:-1]

        if flag == 0x00 and len(payload) == 17:
            header = payload
            continue
        if flag == 0xFF and header is not None:
            file_type = header[0]
            name = header[1:11].decode("latin-1").rstrip()
            length = header[11] | (header[12] << 8)
            param1 = header[13] | (header[14] << 8)
            param2 = header[15] | (header[16] << 8)
            header = None
            if file_type != 0:
                kind = {1: "number array", 2: "character array", 3: "CODE"}
                warnings.append(
                    f"skipped {kind.get(file_type, 'unknown')} block '{name}'"
                )
                continue
            body = payload[:length] if length <= len(payload) else payload
            if 0 < param2 <= len(body):
                body = body[:param2]  # drop the variables area
            autostart = param1 if param1 < 32768 else None
            yield sanitize(name), body, autostart


def convert_file(path, outdir, force, used_names):
    warnings = []
    data = path.read_bytes()
    if data[:8] == b"ZXTape!\x1a":
        blocks = tzx_blocks(data, warnings)
    else:
        blocks = tap_blocks(data)

    programs = list(extract_programs(blocks, warnings))
    for warning in warnings:
        print(f"  note: {warning}")
    if not programs:
        print(f"  {path.name}: no BASIC programs found")
        return 0

    # single program per tape: prefer the tape's own filename (the Fuse
    # savehook wrote one program per <name>.tzx)
    written = 0
    for index, (name, body, autostart) in enumerate(programs):
        if len(programs) == 1:
            name = sanitize(path.stem)
        base = name
        n = 2
        while name in used_names:
            name = f"{base}-{n}"
            n += 1
        used_names.add(name)

        out = outdir / f"{name}.bas"
        if out.exists() and not force:
            print(f"  {out} exists, skipping (use --force to overwrite)")
            continue
        listing_warnings = []
        text = detokenize(body, listing_warnings)
        for warning in listing_warnings:
            print(f"  note: {warning}")
        out.write_text(text, encoding="utf-8")
        extra = f", autostart line {autostart} dropped" if autostart else ""
        print(f"  {path.name} -> {out} ({len(text.splitlines())} lines{extra})")
        written += 1
    return written


def main():
    parser = argparse.ArgumentParser(
        description="Convert Fuse-era .tzx/.tap BASIC saves to kiosk .bas listings"
    )
    parser.add_argument("inputs", nargs="+", type=pathlib.Path,
                        help="tape files, or directories full of them")
    parser.add_argument("-o", "--outdir", type=pathlib.Path,
                        default=pathlib.Path("."), help="output directory")
    parser.add_argument("--force", action="store_true",
                        help="overwrite existing .bas files")
    args = parser.parse_args()

    files = []
    for item in args.inputs:
        if item.is_dir():
            files += sorted(
                p for p in item.iterdir()
                if p.suffix.lower() in (".tzx", ".tap")
            )
        else:
            files.append(item)
    if not files:
        sys.exit("no tape files found")

    args.outdir.mkdir(parents=True, exist_ok=True)
    used_names = set()
    total = 0
    for path in files:
        print(f"{path}:")
        try:
            total += convert_file(path, args.outdir, args.force, used_names)
        except Exception as error:  # keep going over a broken tape
            print(f"  ERROR: {error}")
    print(f"{total} program(s) written to {args.outdir}")


if __name__ == "__main__":
    main()
