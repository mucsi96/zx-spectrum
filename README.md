# ZX Spectrum Next kiosk — ZEsarUX with host-disk NextBASIC

Runs the **ZX Spectrum Next** (NextZXOS / NextBASIC) in the **ZEsarUX**
emulator, patched so that the BASIC commands work directly on plain files in
a host directory — no SD-image juggling, no tape files:

| In NextBASIC        | On the host                              |
|---------------------|------------------------------------------|
| `SAVE "lib"`        | writes `~/programs/lib.bas`              |
| `LOAD "game"`       | reads `~/programs/game.bas`              |
| `MERGE "lib"`       | merges `~/programs/lib.bas`              |
| `SAVE "@"`          | re-saves to the last file used           |
| `ERASE "lib"`       | deletes `~/programs/lib.bas`             |

The `.bas` files are **plain text BASIC listings** — one numbered line per
text line, exactly what `LIST` shows — and they are the source of truth:
edit them in any editor, version them, sync them. SAVE detokenizes the
program to text, LOAD tokenizes it back. Everything else on the emulated SD
card (NextZXOS itself, the Browser, demos) keeps working — only plain
filenames are redirected to the host.

The previous Fuse-based 48K setup is preserved in [README-fuse.md](README-fuse.md).

---

## Repository layout

```
zesarux-nextbasic-hostdisk.patch   emulator patch 1: host-disk SAVE/LOAD (git-apply-able diff)
zesarux-nextbasic-highlight.patch  emulator patch 2: editor syntax highlighting
spectrum-launcher.sh               console program-picker / kiosk launcher
programs/*.bas                     program listings (the host format: plain text)
tools/tzx2bas.py                   converter: old Fuse .tzx/.tap saves -> listings
flake.nix                          Nix flake: patched emulator + `spectrum` runner
ansible/                           provisioning for the Raspberry Pi over SSH
```

## The patches

Both patches apply against
[ZEsarUX](https://github.com/chernandezba/zesarux) master (cut and tested at
`7d33f6b`, v13.1-SN), independently and in any order:

```bash
git clone https://github.com/chernandezba/zesarux && cd zesarux
git apply /path/to/zesarux-nextbasic-hostdisk.patch
git apply /path/to/zesarux-nextbasic-highlight.patch
cd src && ./configure --enable-sdl2 && make -j$(nproc)
```

### 1. Host-disk SAVE/LOAD (`zesarux-nextbasic-hostdisk.patch`)

It hooks the +3DOS API jump table (`DOS_OPEN` 0106h, `DOS_READ` 0112h, …)
that NextZXOS uses for *all* file access, but only when the TBBlue runs in
+3e mode with the DOS ROM paged in. Plain names are served from the host
directory; anything with a drive, path, extension or wildcard falls through
to the real NextZXOS. On SAVE the program is detokenized into a text
listing; on LOAD a listing is tokenized back (classic 48K keyword set,
including the hidden five-byte number forms — legacy raw tokenized files
are still accepted). The PLUS3DOS header and the variables area never reach
the host file, and saves are atomic (temp file + rename).

The patch is inert unless `ZESARUX_NEXTBASIC_DIR` is set:

```bash
ZESARUX_NEXTBASIC_DIR=$HOME/programs \
zesarux --machine tbblue --enable-mmc --enable-divmmc-ports --mmc-file tbblue.mmc
```

Optional: `ZESARUX_NEXTBASIC_AUTOLOAD=name` boots straight into
`<dir>/name.bas` — the handler serves a synthetic `autoexec.bas` that LOADs
the program with an autostart line, so it RUNs unattended (this is how the
launcher starts programs). `ZESARUX_NEXTBASIC_AUTOLOAD=-` suppresses any
real autoexec and boots to the NextZXOS menu.

The bundled `tbblue.mmc` NextZXOS SD image ships with the ZEsarUX sources,
so no extra downloads are needed.

### 2. Editor syntax highlighting (`zesarux-nextbasic-highlight.patch`)

Colours the NextBASIC full-screen editor, SpecNext-IDE style, live while
you scroll and type:

| Token                                       | Colour  |
|---------------------------------------------|---------|
| statements (`PRINT`, `LET`, `GO TO`, …)     | blue    |
| functions (`RND`, `INT`, `CHR$`, …)         | magenta |
| numbers                                     | red     |
| strings                                     | green   |
| `REM` comment text                          | cyan    |
| line numbers, variables, operators          | black   |

The editor draws each character in its own 8×8 attribute cell, so the
patch recolours the ink per cell once per frame: it recognizes the
characters on the ULA screen by CRC fingerprints of their glyph bitmaps
(the editor font of the bundled NextZXOS), parses rows that start with a
line number (plus wrapped continuations), and rewrites only attribute
cells that carry the editor's own colour. Program output during `RUN`,
the menus and the cursor stay untouched; if a future NextZXOS changes the
editor font, the effect gracefully degrades to no colouring.

Enabled by `ZESARUX_NEXTBASIC_HIGHLIGHT=1` (the launcher and the flake
runner set it).

### Known limitations (all inherent to the ROM, not the patch)

- `SAVE ""` cannot re-save: the NextBASIC ROM rejects an empty filename
  with *Invalid file name* before the DOS layer is reached. Use `SAVE "@"`.
- `NEW` returns to the NextZXOS main menu (pick *NextBASIC* to continue).
- When an auto-loaded program ends, NextZXOS shows its menu.
- `SAVE "name" LINE 10` autostart lines are not stored in the host file.

### Special characters in listings

Block graphics and the other non-ASCII ZX characters survive the text
round trip:

| ZX character            | In the listing                                    |
|-------------------------|---------------------------------------------------|
| block graphics (128–143)| Unicode quadrant characters `▘▝▀▖▌▞▛▗▚▐▜▄▙▟█` (the empty block 128 is `\..`) |
| UDGs A–U (144–164)      | `\a` … `\u` (zmakebas convention)                 |
| `£`, `©`                | UTF-8 `£`, `©`                                    |
| anything else           | `\xHH` (lossless fallback, e.g. colour codes)     |

`LOAD` also accepts zmakebas-style block escapes (`\` plus two column
characters from `. ' , :` meaning none/top/bottom/both, left column
first — `\':` is the ▛ block), so listings written for zmakebas work too.

## Testing on WSL2 (Windows 11) with Nix flakes

WSLg gives WSL2 a display and audio, so the SDL2 build runs as-is:

```bash
nix run github:mucsi96/zx-spectrum            # boot to the NextZXOS menu
nix run github:mucsi96/zx-spectrum#spectrum -- 06-ratespiel   # boot into a program
nix run github:mucsi96/zx-spectrum#menu       # the kiosk program-picker menu
```

or from a checkout: `nix develop`, then `nix run .#spectrum`. The runner

- builds ZEsarUX `7d33f6b` with the patch applied (pinned via flake input),
- keeps state in `~/.local/share/zx-spectrum-next/` (private `tbblue.mmc`
  copy + the `programs/` host directory),
- seeds missing programs from the repo's listings, never overwriting your
  saved work.

First ever NextZXOS boot shows its video-mode test card once — press ENTER.
Press **F10** to quit the emulator.

## Installing the Raspberry Pi kiosk over SSH (Ansible)

Flash Raspberry Pi OS Lite with SSH enabled (Imager settings), then:

```bash
cd ansible
cp inventory.example.ini inventory.ini    # set your host/user
ansible-playbook -i inventory.ini playbook.yml
```

The playbook (idempotent — safe to re-run):

- installs build deps, fetches ZEsarUX at the pinned revision, applies the
  patch, builds with SDL2 (KMS/DRM — no X server) and installs it
  (rebuilds only when the revision or the patch changes),
- installs `spectrum-launcher.sh` and starts it on tty1 via console
  autologin,
- seeds `~/programs` from `programs/*.bas` (existing files are never
  overwritten — the kid's work wins),
- lets the kiosk user power off from the menu without a password.

## The launcher

`spectrum-launcher.sh` shows a `dialog` menu of everything in `~/programs`:
pick a program and the Next boots straight into it; *New program* boots to
the NextZXOS menu; *Shut down* powers the Pi off. The menu sizes itself to
the console, so all rows of the display are used for program entries —
no scrolling until the list outgrows the screen. F10 in the emulator
returns to the menu.

## Program files

Host programs are ordinary text listings:

```
10 LET N=INT(RND*100)
20 PRINT "Auf welche Zahl tippst du?"
30 INPUT G
```

`SAVE` in the emulator writes exactly this format, so the files in
`programs/` and the files a kid saves on the kiosk are the same thing —
copy them back into the repo to version new programs.

## Migrating saves from the old Fuse setup

`tools/tzx2bas.py` converts the tapes the Fuse 48K kiosk wrote
(`~/tapes/*.tzx` from the savehook patch, or an accumulated `tape.tzx`)
into listings — one `.bas` per BASIC program found on the tapes:

```bash
tools/tzx2bas.py ~/tapes -o ~/programs        # a directory of tapes
tools/tzx2bas.py tape.tzx -o ~/programs       # a single multi-program tape
```

It reads `.tzx` and `.tap`, verifies block checksums, expands the 48K
tokens, drops the hidden number bytes and the variables area, and maps
block graphics/UDGs/`£`/`©` with the same conventions as the emulator —
so the results LOAD directly in NextBASIC. Existing `.bas` files are
never overwritten (`--force` to override); CODE/array blocks are skipped
with a note, and tape-autostart lines are reported (the kiosk launcher
auto-RUNs programs anyway). Python 3 only, no dependencies.
