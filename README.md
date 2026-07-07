# Fuse (ZX Spectrum) — flash-and-go autostart on Raspberry Pi 3B

Boots a Raspberry Pi 3B straight into the **Fuse** ZX Spectrum emulator, fullscreen,
with **no desktop environment**. Almost everything is provisioned by **cloud-init** on
first boot, so you barely touch the Pi itself.

- **Hardware:** Raspberry Pi 3B
- **OS:** Raspberry Pi OS **Lite**, Debian 13 **Trixie** (image dated 24 Nov 2025 or newer — these ship cloud-init)
- **Imager:** Raspberry Pi **Imager 2.0.6+** (older Imager can't customise Trixie)
- **Emulator:** Fuse **1.8.0**, built from source with **native SDL2**
- **Display path:** SDL2 → KMS/DRM, no X server

---

## Why build from source instead of `apt install`?

The packaged Fuse on Trixie is **1.6.0**, built against the **SDL 1.2** API, which on Trixie
is provided by the **sdl12-compat** shim (SDL 1.2 on top of SDL2). Its OpenGL-scaling path
does **not** work headless under `kmsdrm` — you get a **black screen, no error**.

Fuse **1.8.0** is the first release with native **SDL 2**, so it talks to SDL2's `kmsdrm`
backend directly, auto-selects the correct display device, and just works. Hence the source build.

---

# Part A — The cloud-init way (recommended)

Raspberry Pi OS Trixie uses cloud-init for first-boot setup. After flashing, the FAT32 boot
partition (`bootfs`) contains three files: **`user-data`**, **`network-config`**, **`meta-data`**.
We let Imager fill in the tricky identity/Wi-Fi parts, then add a Fuse block to `user-data`.

## Step 1 — Flash with Imager and set the basics

In Raspberry Pi Imager, choose **Raspberry Pi OS Lite (64-bit, Trixie)**, then open the
customisation (gear / "Edit settings") and set:

- **Username + password** (remember the username — you'll reference it below)
- **Wi-Fi** SSID, password, and **Wi-Fi country**
- **Hostname**
- **Enable SSH** (paste a public key if you have one — then you never type a password)
- **Locale / timezone**

Imager writes correct `user-data` + `network-config` from these. Write the image, but **don't
eject yet.**

## Step 2 — Add the Fuse block to `user-data`

Open the `bootfs` partition on your computer and edit **`user-data`**. It already starts with
`#cloud-config` and has a `users:` section from Imager. **Merge** the keys below into it — add
each top-level key once; if a key (e.g. `runcmd:`) already exists, append the items to the
existing list instead of adding a second copy.

```yaml
# ---- add to the existing user-data (do not create a second #cloud-config) ----

package_update: true
packages:
  - build-essential
  - pkg-config
  - libsdl2-dev
  - libpng-dev
  - libxml2-dev
  - zlib1g-dev
  - libgcrypt20-dev
  - libbz2-dev
  - libasound2-dev
  - dialog

write_files:
  # 3-line autostart, staged here and installed into the user's home by the script below.
  # No `exec`, no loop: if Fuse exits you land at a normal shell prompt — never locked out.
  - path: /etc/fuse/bash_profile
    permissions: '0644'
    content: |
      if [ "$(tty)" = "/dev/tty1" ]; then
        ~/spectrum-launcher.sh
      fi

  - path: /usr/local/sbin/setup-fuse.sh
    permissions: '0755'
    content: |
      #!/bin/bash
      set -euxo pipefail

      # ===== CONFIG — the only lines you normally touch ==========================
      FUSE_VER="1.8.0"        # pin a version ("1.8.0", "1.9.0", ...) or "auto" for newest
      LIBSPEC_VER="1.6.0"     # libspectrum version to build ("1.6.0", ...) or "auto"
      USER_NAME="pi"          # <<< set to the username you chose in Imager
      # ===========================================================================

      HOME_DIR="$(getent passwd "$USER_NAME" | cut -d: -f6)"
      exec >>/var/log/fuse-build.log 2>&1

      # Resolve "auto" to the newest source tarball on SourceForge (reads the file RSS once).
      sf_latest() {   # $1 = subdir (fuse|libspectrum)   $2 = filename prefix (fuse-|libspectrum-)
        wget -qO- "https://sourceforge.net/projects/fuse-emulator/rss?path=/$1" 2>/dev/null \
          | grep -oE "$2[0-9]+(\.[0-9]+)+\.tar\.gz" \
          | sed -E "s/.*$2//; s/\.tar\.gz//" \
          | sort -V | tail -n1
      }
      [ "$FUSE_VER" = auto ]    && FUSE_VER="$(sf_latest fuse fuse-)"
      [ "$LIBSPEC_VER" = auto ] && LIBSPEC_VER="$(sf_latest libspectrum libspectrum-)"

      mkdir -p /usr/local/src && cd /usr/local/src

      # libspectrum: always built from source
      wget -O "libspectrum-${LIBSPEC_VER}.tar.gz" "https://sourceforge.net/projects/fuse-emulator/files/libspectrum/${LIBSPEC_VER}/libspectrum-${LIBSPEC_VER}.tar.gz/download"
      tar xf "libspectrum-${LIBSPEC_VER}.tar.gz"
      ( cd "libspectrum-${LIBSPEC_VER}" && ./configure --with-fake-glib && make -j"$(nproc)" && make install && ldconfig )

      # Fuse with native SDL2
      wget -O "fuse-${FUSE_VER}.tar.gz" "https://sourceforge.net/projects/fuse-emulator/files/fuse/${FUSE_VER}/fuse-${FUSE_VER}.tar.gz/download"
      tar xf "fuse-${FUSE_VER}.tar.gz"
      ( cd "fuse-${FUSE_VER}" && ./configure --without-gtk --with-sdl && make -j"$(nproc)" && make install && ldconfig )

      # Install the autostart into the user's home, owned by them
      install -m 0644 -o "$USER_NAME" -g "$USER_NAME" /etc/fuse/bash_profile "${HOME_DIR}/.bash_profile"

      # Persistent tape for SAVE/LOAD — created once (empty TZX), never clobbered on re-provision
      if [ ! -f "${HOME_DIR}/tape.tzx" ]; then
        printf 'ZXTape!\x1a\x01\x14' > "${HOME_DIR}/tape.tzx"
        chown "${USER_NAME}:${USER_NAME}" "${HOME_DIR}/tape.tzx"
      fi

      touch /var/local/fuse-setup-done

runcmd:
  - [ raspi-config, nonint, do_boot_behaviour, B2 ]   # console autologin on tty1
  - [ /usr/local/sbin/setup-fuse.sh ]
```

The only value you *must* change is `USER_NAME` in the script — set it to the username you chose
in Imager.

**CONFIG block** (top of `setup-fuse.sh`):

- `FUSE_VER` / `LIBSPEC_VER` — pin exact versions (default `1.8.0` / `1.6.0`), or set either to `auto`
  to build the newest source tarball from SourceForge. There is **no fallback**: if `auto` can't
  resolve a version (or you pin one that doesn't exist), the build fails loudly in the log rather than
  silently using something else. libspectrum is **always built from source** to the chosen version, so
  bumping Fuse to a release needing newer libspectrum just works when you bump both (or set both `auto`).
**Persistent tape (SAVE/LOAD).** First boot creates an empty tape at `~/tape.tzx` (only if absent, so
your saved programs survive re-provisioning). Fuse starts with that tape **inserted but not auto-loaded**:
`--full-screen --no-statusbar --no-auto-load --tape ~/tape.tzx`. Tape traps are on by default, so inside
the Spectrum `LOAD ""` reads from the tape and `SAVE "name"` records to it. Persisting those saves to disk
is a manual step — see *SAVE / LOAD and saving your work* below.

## Step 3 — Boot and wait

Eject, boot the Pi. On **first boot** cloud-init installs the packages and compiles
libspectrum + Fuse. On a Pi 3B this takes roughly **10–15 minutes**. The board is reachable by
SSH the whole time.

Watch progress (optional) over SSH:
```bash
tail -f /var/log/fuse-build.log          # the build
tail -f /var/log/cloud-init-output.log   # everything cloud-init runs
ls /var/local/fuse-setup-done            # appears when the build finished
```

## Step 4 — Reboot once

Autologin was enabled *during* first boot, after the console had already logged in, and the
build finishes after that — so **Fuse won't be running on the very first boot**. Once
`fuse-setup-done` exists:
```bash
sudo reboot
```
It now autologins on tty1 and drops straight into fullscreen Fuse. Every boot after that is
flash-and-go.

---

## Using it

- **F1** — open Fuse's in-app menu (arrow keys + Enter; there's no window manager).
- **File → Exit**, or press **F10**, to quit. Quitting returns you to a shell prompt.
- Over SSH you can stop it with `pkill -f fuse`.

### SAVE / LOAD and saving your work

The persistent tape `~/tape.tzx` is inserted at boot but not auto-run, so you land at BASIC. With tape
traps on (the default):

- `LOAD ""` — load the next program from the tape (your previously saved work).
- `SAVE "name"` — record a program onto the tape.

**Persistence is a manual step.** `SAVE` writes into Fuse's *in-memory* copy of the tape; it is **not**
flushed to disk automatically, and there's no reliable save-on-exit. To keep your work across reboots:
press **F1 → Media → Tape → Write**, then save over `~/tape.tzx` (confirm the overwrite). On the next boot
the tape is re-inserted and `LOAD ""` sees your saved programs.

First-time check: the tape starts empty, so do `SAVE "test"`, then Media → Tape → Write to `~/tape.tzx`,
reboot, and `LOAD ""` — it should come back. Keep "Confirm actions" enabled (default) so a stray reset
doesn't silently discard the in-memory tape.

---

# Part B — Manual reference (understanding / troubleshooting)

Everything cloud-init does above, by hand — useful for fixing a running system or building
without cloud-init.

**Console autologin:** `sudo raspi-config` → System Options → Boot / Auto Login → Console Autologin.

**Build dependencies:**
```bash
sudo apt update
sudo apt install build-essential pkg-config libsdl2-dev libpng-dev \
  libxml2-dev zlib1g-dev libgcrypt20-dev libbz2-dev libasound2-dev
```

Pick your versions once, then reuse them below:
```bash
FUSE_VER=1.8.0        # or 1.9.0, etc.
LIBSPEC_VER=1.6.0
```

**libspectrum (always built from source):**
```bash
cd ~
wget -O "libspectrum-${LIBSPEC_VER}.tar.gz" "https://sourceforge.net/projects/fuse-emulator/files/libspectrum/${LIBSPEC_VER}/libspectrum-${LIBSPEC_VER}.tar.gz/download"
tar xf "libspectrum-${LIBSPEC_VER}.tar.gz" && cd "libspectrum-${LIBSPEC_VER}"
./configure --with-fake-glib && make -j4 && sudo make install && sudo ldconfig && cd ~
```

**Fuse with SDL2:**
```bash
cd ~
wget -O "fuse-${FUSE_VER}.tar.gz" "https://sourceforge.net/projects/fuse-emulator/files/fuse/${FUSE_VER}/fuse-${FUSE_VER}.tar.gz/download"
tar xf "fuse-${FUSE_VER}.tar.gz" && cd "fuse-${FUSE_VER}"
./configure --without-gtk --with-sdl      # summary should show UI = SDL, SDL2 detected
make -j4 && sudo make install && sudo ldconfig && cd ~
```

To find the current newest versions by hand, browse
<https://sourceforge.net/projects/fuse-emulator/files/fuse/> and
<https://sourceforge.net/projects/fuse-emulator/files/libspectrum/>.
The binary is **`/usr/local/bin/fuse`** (a source SDL build is named `fuse`, not `fuse-sdl`),
and it bundles its own ROMs.

**Verify it linked SDL2, not the compat layer:**
```bash
ldd /usr/local/bin/fuse | grep -i sdl      # want: libSDL2-2.0.so.0
```

**Autostart** — put exactly this (and nothing more) in `~/.bash_profile`. It hides the status icons
and inserts (without auto-running) the persistent tape for SAVE/LOAD:
```bash
if [ "$(tty)" = "/dev/tty1" ]; then
    if [ -f "$HOME/tape.tzx" ]; then
        fuse --full-screen --no-statusbar --no-auto-load --tape "$HOME/tape.tzx"
    else
        fuse --full-screen --no-statusbar
    fi
fi
```
Create the empty tape once: `printf 'ZXTape!\x1a\x01\x14' > ~/tape.tzx`

---

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `apt` Fuse: black screen under kmsdrm | 1.6.0 is SDL1.2 via sdl12-compat; GL-scaling fails headless | Build 1.8.0 with native SDL2 |
| Fuse launches **3× / loops**, can't exit | `exec` + console autologin: shell is replaced, getty re-logs-in, re-runs Fuse | Use the plain `fuse --full-screen` block — **no `exec`, no `while` loop** |
| Duplicate launches | The block is in `.bash_profile` more than once (or also in `.profile`) | `grep -n fuse ~/.bash_profile ~/.profile ~/.bashrc` — keep one copy in `.bash_profile` |
| Locked at black screen with blinking `_` | Shell alive but display left in graphics mode | SSH in and `pkill -f fuse`; or type `reset` blind; or Ctrl+Alt+F2 to another console |
| `ldd` shows `libSDL-1.2` | `libsdl2-dev` missing at configure time | Install it, rebuild |
| Imager customisation greyed out / not applied | Old Imager on a Trixie image | Use Imager **2.0.6+** |
| Verify the GL/KMS stack itself | — | `sudo apt install kmscube && kmscube` → spinning cube = stack OK |

> **Note on `SDL_KMSDRM_DEVICE_INDEX`:** you only need this with the old SDL1.2/compat build,
> which sometimes grabs the render-only DRM node. The native-SDL2 Fuse 1.8.0 selects the
> connected display node itself, so no index variable is required.

---

## Version notes

- Fuse **1.9.0** (mid-2026) also has SDL2 and works with the same steps — just change the
  version numbers in the URLs. It may want a newer libspectrum; the source-build fallback covers that.
- Debian sid already packages `fuse-emulator-sdl 1.8.0`, so a future Raspberry Pi OS may ship a
  native-SDL2 Fuse. After any `apt` install, check with `ldd $(which fuse-sdl) | grep -i sdl`; if
  it shows `libSDL2`, you can skip the source build entirely.
- No-Imager path: cloud-init also reads hand-written `user-data` + `network-config` (+ an empty
  `meta-data`) placed directly on the boot partition. `network-config` is netplan v2, e.g. a
  `wifis:` block with your SSID/password. Imager just spares you the YAML and the password hashing.