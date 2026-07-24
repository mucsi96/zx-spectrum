#!/usr/bin/env bash
#
# spectrum-launcher.sh — program picker for the ZEsarUX ZX Spectrum Next kiosk.
#
# Shows a menu of saved programs (one raw tokenized .bas per program in
# ~/programs). Selecting one boots NextZXOS and auto-LOADs + RUNs it, via the
# NextBASIC host-disk patch (ZESARUX_NEXTBASIC_* environment variables).
# "New program" boots to the NextZXOS menu (pick NextBASIC there).
# Quitting ZEsarUX (F10) returns here.
#
# Inside BASIC, SAVE "name" writes ~/programs/name.bas directly on the host,
# LOAD "name" reads it, SAVE "@" re-saves to the last used file, and
# ERASE "name" deletes it. The .bas files are the source of truth.
#
# The menu auto-sizes to the console so as many programs as possible are
# visible without scrolling.
#
# Requires: dialog   (sudo apt install dialog)

set -u

PROGRAMS="${SPECTRUM_PROGRAMS:-$HOME/programs}"
MMC="${SPECTRUM_MMC:-$HOME/tbblue.mmc}"              # private writable SD image

# The patched build: /usr/local on the Pi kiosk; on other machines take it
# from PATH (e.g. nix run .#menu puts it there) or the ZESARUX variable
ZESARUX="${ZESARUX:-$(command -v zesarux || echo /usr/local/bin/zesarux)}"
SHARE="${ZESARUX_SHARE:-$(dirname "$ZESARUX")/../share/zesarux}"

if [ ! -x "$ZESARUX" ]; then
  echo "zesarux not found ($ZESARUX)."
  echo "On the Pi: run the Ansible playbook first."
  echo "On a Nix machine: use    nix run .#menu"
  exit 1
fi

ZOPTS=( --machine tbblue --enable-mmc --enable-divmmc-ports
        --mmc-file "$MMC"
        --fullscreen --disablefooter --nowelcomemessage --quickexit
        --hidemousepointer                           # no mouse cursor over the emulator
        --stats-disable-check-updates                # no "new version" popup
        --stats-disable-check-yesterday-users
        --stats-send-already-asked                   # no first-run statistics question
        --tbblue-autoconfigure-sd-already-asked
        --def-f-function F10 ExitEmulator )          # F10 quits, like Fuse

mkdir -p "$PROGRAMS"
export ZESARUX_NEXTBASIC_DIR="$PROGRAMS"
export ZESARUX_NEXTBASIC_HIGHLIGHT=1   # syntax colours in the NextBASIC editor

# First run: take a private copy of the NextZXOS SD image, so OS-side state
# stays per-user and a broken image is fixed by deleting ~/tbblue.mmc
if [ ! -f "$MMC" ]; then
  cp "$SHARE/tbblue.mmc" "$MMC" && chmod 644 "$MMC"
fi

while true; do
  # Build the menu: fixed entries first, then one row per saved program.
  menu=( "new" "New program (NextZXOS menu -> NextBASIC)" )

  shopt -s nullglob
  i=0
  declare -A map=()
  for f in "$PROGRAMS"/*.bas; do
    tag="p$i"
    menu+=( "$tag" "$(basename "$f" .bas)" )
    map["$tag"]="$f"
    i=$((i+1))
  done
  shopt -u nullglob

  menu+=( "off" "Shut down (kiosk) / exit menu" )

  # Fill the whole console: dialog needs 7 rows of chrome around the list,
  # so every remaining row shows one program — no scrolling until the
  # program count outgrows the screen.
  rows=$(tput lines 2>/dev/null || echo 24)
  cols=$(tput cols  2>/dev/null || echo 80)
  height=$(( rows - 2 )); [ "$height" -lt 15 ] && height=15
  width=$(( cols - 4 ));  [ "$width" -gt 74 ] && width=74
  listheight=$(( height - 7 ))

  choice="$(dialog --clear --stdout --no-cancel \
            --title " ZX Spectrum Next " \
            --menu "Choose a program   (in the emulator, press F10 to come back here):" \
            "$height" "$width" "$listheight" "${menu[@]}")" || { clear; continue; }

  clear
  case "$choice" in
    new)  ZESARUX_NEXTBASIC_AUTOLOAD="-" "$ZESARUX" "${ZOPTS[@]}" ;;
    off)  clear
          if [ "$(tty)" = "/dev/tty1" ]; then
            sudo systemctl poweroff             # the kiosk console
          else
            exit 0                              # desktop/WSL2: just leave
          fi ;;
    *)    ZESARUX_NEXTBASIC_AUTOLOAD="$(basename "${map[$choice]}" .bas)" \
            "$ZESARUX" "${ZOPTS[@]}" ;;
  esac
done
