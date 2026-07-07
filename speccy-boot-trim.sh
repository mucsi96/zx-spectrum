#!/usr/bin/env bash
#
# boot-trim.sh — trim Raspberry Pi OS Lite (Trixie) boot time for a
# single-purpose appliance (e.g. a Fuse / ZX Spectrum kiosk).
#
# Safe to run over SSH: it does NOT touch NetworkManager, SSH, or your active
# session — only things that are pure boot-time overhead for a kiosk.
# It is idempotent (safe to re-run) and logs everything to the terminal AND
# to a timestamped file in /var/log.
#
# Usage:
#   sudo bash boot-trim.sh            # apply trims, then reboot yourself
#   sudo bash boot-trim.sh --reboot   # apply trims and reboot automatically
#
# A reboot is required for the changes to take effect.
#
# NOT done automatically (left to you, since it can break boot on some setups):
#   * disabling the initramfs (auto_initramfs) — test manually if you want it.
#
# Revert: restore the *.boot-trim.bak.* backups this script makes, and
# re-enable any unit with:  sudo systemctl enable --now <unit>

set -uo pipefail

# --- must run as root -------------------------------------------------------
if [ "$(id -u)" -ne 0 ]; then
  exec sudo -- bash "$0" "$@"
fi

STAMP="$(date +%Y%m%d-%H%M%S)"
LOG="/var/log/boot-trim-${STAMP}.log"

# Send all stdout/stderr to the terminal and the log file at once.
exec > >(tee -a "$LOG") 2>&1

REBOOT=0
[ "${1:-}" = "--reboot" ] && REBOOT=1

log() { printf '%s  %s\n' "$(date +%H:%M:%S)" "$*"; }
hr()  { printf -- '------------------------------------------------------------\n'; }

log "boot-trim starting — full log at $LOG"
hr

# --- baseline (timing of the PREVIOUS boot) --------------------------------
log "Boot timing of the previous boot (compare after reboot):"
if base="$(systemd-analyze 2>&1)"; then
  printf '%s\n' "$base" | sed 's/^/    /'
else
  log "    (systemd-analyze not available yet)"
fi
hr

# --- locate the firmware boot files ----------------------------------------
if   [ -f /boot/firmware/config.txt ]; then BOOTDIR=/boot/firmware
elif [ -f /boot/config.txt ];          then BOOTDIR=/boot
else BOOTDIR=""; fi
CONFIG="${BOOTDIR:+$BOOTDIR/config.txt}"
CMDLINE="${BOOTDIR:+$BOOTDIR/cmdline.txt}"
log "Firmware boot directory: ${BOOTDIR:-<not found>}"
hr

# --- helper: disable a systemd unit if it exists ---------------------------
disable_unit() {
  local unit="$1" out
  if ! systemctl cat "$unit" >/dev/null 2>&1; then
    log "  $unit — not present, skipping"
    return 0
  fi
  if out="$(systemctl disable --now "$unit" 2>&1)"; then
    log "  $unit — disabled"
  else
    log "  $unit — could not disable (static or already off)"
  fi
  [ -n "$out" ] && printf '%s\n' "$out" | sed 's/^/        /'
}

# --- 1) cloud-init (biggest single win once provisioning is done) ----------
log "[1] cloud-init"
if [ -d /etc/cloud ]; then
  if [ -e /etc/cloud/cloud-init.disabled ]; then
    log "  already disabled"
  else
    touch /etc/cloud/cloud-init.disabled
    log "  disabled (created /etc/cloud/cloud-init.disabled)"
    log "  NOTE: re-flash the card if you ever want cloud-init provisioning again"
  fi
else
  log "  not installed, skipping"
fi
hr

# --- 2) don't block boot waiting for the network ---------------------------
log "[2] network wait-online"
disable_unit NetworkManager-wait-online.service
disable_unit systemd-networkd-wait-online.service
hr

# --- 3) Bluetooth (services + free the UART via overlay, added below) ------
log "[3] Bluetooth services"
disable_unit bluetooth.service
disable_unit hciuart.service
hr

# --- 4) misc daemons a kiosk doesn't need ----------------------------------
log "[4] Misc daemons"
disable_unit triggerhappy.service
disable_unit triggerhappy.socket
disable_unit ModemManager.service
disable_unit avahi-daemon.service
disable_unit avahi-daemon.socket
hr

# --- 5) background timers (reduce post-boot SD-card thrash) -----------------
log "[5] Background timers"
for t in apt-daily.timer apt-daily-upgrade.timer man-db.timer \
         fstrim.timer e2scrub_all.timer; do
  disable_unit "$t"
done
hr

# --- 6) swap ----------------------------------------------------------------
log "[6] Swap (dphys-swapfile)"
if systemctl cat dphys-swapfile.service >/dev/null 2>&1; then
  swap_out="$(dphys-swapfile swapoff 2>&1)" || true
  [ -n "$swap_out" ] && printf '%s\n' "$swap_out" | sed 's/^/        /'
  disable_unit dphys-swapfile.service
else
  log "  dphys-swapfile not present, skipping"
fi
hr

# --- 7) firmware config: splash off, no boot delay, disable BT overlay -----
log "[7] Firmware config (config.txt)"
if [ -n "$CONFIG" ]; then
  cp -a "$CONFIG" "$CONFIG.boot-trim.bak.$STAMP"
  log "  backup -> $CONFIG.boot-trim.bak.$STAMP"
  MARKER="# >>> boot-trim additions >>>"
  if grep -qF "$MARKER" "$CONFIG"; then
    log "  boot-trim block already present, skipping"
  else
    cat >> "$CONFIG" <<EOF

$MARKER
[all]
disable_splash=1
boot_delay=0
dtoverlay=disable-bt
# <<< boot-trim additions <<<
EOF
    log "  appended: disable_splash=1, boot_delay=0, dtoverlay=disable-bt (under [all])"
  fi
else
  log "  config.txt not found, skipping"
fi
hr

# --- 8) quieter kernel boot (cmdline.txt) ----------------------------------
log "[8] Kernel cmdline (quiet)"
if [ -n "$CMDLINE" ] && [ -f "$CMDLINE" ]; then
  cp -a "$CMDLINE" "$CMDLINE.boot-trim.bak.$STAMP"
  log "  backup -> $CMDLINE.boot-trim.bak.$STAMP"
  if grep -qw quiet "$CMDLINE"; then
    log "  'quiet' already present"
  else
    sed -i '1 s/[[:space:]]*$/ quiet/' "$CMDLINE"
    log "  added 'quiet' to the kernel command line"
  fi
else
  log "  cmdline.txt not found, skipping"
fi
hr

# --- summary ----------------------------------------------------------------
log "All done."
log "Backups made:"
log "  ${CONFIG:-n/a}.boot-trim.bak.$STAMP"
log "  ${CMDLINE:-n/a}.boot-trim.bak.$STAMP"
log ""
log "Reboot required. After it comes back, measure the improvement with:"
log "    systemd-analyze          # total"
log "    systemd-analyze blame    # slowest units"
log "Log saved at: $LOG"
hr

if [ "$REBOOT" -eq 1 ]; then
  log "Rebooting now (--reboot given)…"
  sync
  sleep 2
  systemctl reboot
else
  log "Run 'sudo reboot' when you're ready."
fi