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

PROGRAMS="$HOME/programs"
ZESARUX="/usr/local/bin/zesarux"                     # the patched build
SHARE="/usr/local/share/zesarux"
MMC="$HOME/tbblue.mmc"                               # private writable SD image

ZOPTS=( --machine tbblue --enable-mmc --enable-divmmc-ports
        --mmc-file "$MMC"
        --fullscreen --disablefooter --nowelcomemessage --quickexit
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

  menu+=( "off" "Shut down" )

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
    off)  clear; sudo systemctl poweroff ;;   # local console: allowed via polkit
    *)    ZESARUX_NEXTBASIC_AUTOLOAD="$(basename "${map[$choice]}" .bas)" \
            "$ZESARUX" "${ZOPTS[@]}" ;;
  esac
done
