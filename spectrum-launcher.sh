#!/usr/bin/env bash
#
# spectrum-launcher.sh — program picker for the Fuse ZX Spectrum kiosk.
#
# Shows a menu of saved programs (one .tzx per program in ~/tapes). Selecting
# one launches Fuse with that tape inserted and auto-loading; "New program"
# launches a blank machine. Quitting Fuse (F10) returns here.
#
# SAVE "name" inside Fuse writes ~/tapes/name.tzx directly, via the
# tape_save_trap patch (needs FUSE_SAVE_DIR, exported below). So LOAD is never
# typed by hand — loading is done here by choosing a file.
#
# Requires: dialog   (sudo apt install dialog)

set -u

TAPES="$HOME/tapes"
FUSE="/usr/local/bin/fuse"                 # the patched, SDL2 build
FUSE_OPTS=( --full-screen --no-statusbar ) # note: auto-load left ON

mkdir -p "$TAPES"
export FUSE_SAVE_DIR="$TAPES"              # tells the patched Fuse where to save

while true; do
  # Build the menu: fixed entries first, then one row per saved program.
  menu=( "new" "New program (blank machine)" )

  shopt -s nullglob
  i=0
  declare -A map=()
  for f in "$TAPES"/*.tzx; do
    tag="p$i"
    menu+=( "$tag" "$(basename "$f" .tzx)" )
    map["$tag"]="$f"
    i=$((i+1))
  done
  shopt -u nullglob

  menu+=( "off" "Shut down" )

  choice="$(dialog --clear --stdout --no-cancel \
            --title " ZX Spectrum " \
            --menu "Choose a program   (in Fuse, press F10 to come back here):" \
            20 62 14 "${menu[@]}")" || { clear; continue; }

  clear
  case "$choice" in
    new)  "$FUSE" "${FUSE_OPTS[@]}" ;;
    off)  clear; sudo systemctl poweroff ;;   # local console: allowed via polkit
    *)    "$FUSE" "${FUSE_OPTS[@]}" --tape "${map[$choice]}" ;;
  esac
done