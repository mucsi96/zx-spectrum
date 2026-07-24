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

The `.bas` files are **raw tokenized BASIC** (no 128-byte PLUS3DOS header)
and are the source of truth: version them, sync them, convert them to/from
text listings with `tools/nextbas.py`. Everything else on the emulated SD
card (NextZXOS itself, the Browser, demos) keeps working — only plain
filenames are redirected to the host.

The previous Fuse-based 48K setup is preserved in [README-fuse.md](README-fuse.md).

---

## Repository layout

```
zesarux-nextbasic-hostdisk.patch  the emulator patch (single git-apply-able diff)
spectrum-launcher.sh              console program-picker / kiosk launcher
tools/nextbas.py                  text listing <-> tokenized .bas converter
programs/*.bas                    program listings (text; tokenized on deploy)
flake.nix                         Nix flake: patched emulator + `spectrum` runner
ansible/                          provisioning for the Raspberry Pi over SSH
```

## The patch

`zesarux-nextbasic-hostdisk.patch` applies against
[ZEsarUX](https://github.com/chernandezba/zesarux) master (cut and tested at
`7d33f6b`, v13.1-SN):

```bash
git clone https://github.com/chernandezba/zesarux && cd zesarux
git apply /path/to/zesarux-nextbasic-hostdisk.patch
cd src && ./configure --enable-sdl2 && make -j$(nproc)
```

It hooks the +3DOS API jump table (`DOS_OPEN` 0106h, `DOS_READ` 0112h, …)
that NextZXOS uses for *all* file access, but only when the TBBlue runs in
+3e mode with the DOS ROM paged in. Plain names are served from the host
directory; anything with a drive, path, extension or wildcard falls through
to the real NextZXOS. The PLUS3DOS header is synthesized on LOAD and
stripped on SAVE (the variables area too, so files stay clean tokenized
listings), and saves are atomic (temp file + rename).

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

### Known limitations (all inherent to the ROM, not the patch)

- `SAVE ""` cannot re-save: the NextBASIC ROM rejects an empty filename
  with *Invalid file name* before the DOS layer is reached. Use `SAVE "@"`.
- `NEW` returns to the NextZXOS main menu (pick *NextBASIC* to continue).
- When an auto-loaded program ends, NextZXOS shows its menu.
- `SAVE "name" LINE 10` autostart lines are not stored in the host file.

## Testing on WSL2 (Windows 11) with Nix flakes

WSLg gives WSL2 a display and audio, so the SDL2 build runs as-is:

```bash
nix run github:mucsi96/zx-spectrum            # boot to the NextZXOS menu
nix run github:mucsi96/zx-spectrum#spectrum -- 06-ratespiel   # boot into a program
```

or from a checkout: `nix develop`, then `nix run .#spectrum`. The runner

- builds ZEsarUX `7d33f6b` with the patch applied (pinned via flake input),
- keeps state in `~/.local/share/zx-spectrum-next/` (private `tbblue.mmc`
  copy + the `programs/` host directory),
- seeds missing programs from the repo's text listings (tokenizing them on
  the fly), never overwriting your saved work.

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
- seeds `~/programs` with tokenized versions of `programs/*.bas`
  (existing files are never overwritten — the kid's work wins),
- lets the kiosk user power off from the menu without a password.

## The launcher

`spectrum-launcher.sh` shows a `dialog` menu of everything in `~/programs`:
pick a program and the Next boots straight into it; *New program* boots to
the NextZXOS menu; *Shut down* powers the Pi off. The menu sizes itself to
the console, so all rows of the display are used for program entries —
no scrolling until the list outgrows the screen. F10 in the emulator
returns to the menu.

## Program files

- On the host, programs are raw tokenized BASIC. Convert to and from
  editable text listings:

  ```bash
  tools/nextbas.py detokenize ~/programs/game.bas game.txt
  tools/nextbas.py tokenize   game.txt ~/programs/game.bas
  ```

- The listings in `programs/` stay in text form in the repo; deployment
  (flake runner, Ansible) tokenizes them on the way in.
