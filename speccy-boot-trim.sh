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
#
# WARNING: if cloud-init is provisioning your WiFi at each boot, disabling it
# drops the connection and the Pi never rejoins the network (headless lock-out).
# So before disabling cloud-init we persist the currently-active WiFi into a
# standalone NetworkManager keyfile that survives without cloud-init.
#
# preserve_active_wifi: returns 0 if wlan0's config is (now) safe without
# cloud-init, non-zero if we could not guarantee it.
preserve_active_wifi() {
  # No WiFi in play (e.g. wired-only) -> nothing to preserve.
  [ -d /sys/class/net/wlan0 ] || { log "  no wlan0 interface — no WiFi to preserve"; return 0; }
  if ! command -v nmcli >/dev/null 2>&1; then
    log "  nmcli not found — cannot verify WiFi persistence"
    return 1
  fi

  local con
  con="$(nmcli -t -g GENERAL.CONNECTION device show wlan0 2>/dev/null)"
  if [ -z "$con" ] || [ "$con" = "--" ]; then
    log "  wlan0 is not connected — no active WiFi profile to preserve"
    # Nothing is connected, so disabling cloud-init can't drop a live link.
    return 0
  fi

  # Already a persistent keyfile on disk -> it will survive cloud-init going away.
  if [ -f "/etc/NetworkManager/system-connections/${con}.nmconnection" ]; then
    log "  active WiFi '$con' already persisted as a NetworkManager keyfile — safe"
    return 0
  fi

  # Otherwise clone it to a standalone, autoconnecting profile that NetworkManager
  # owns on disk (independent of cloud-init). clone copies the PSK for us.
  local newname="${con}-persistent"
  if nmcli connection show "$newname" >/dev/null 2>&1; then
    log "  persistent WiFi profile '$newname' already exists — safe"
    return 0
  fi
  if nmcli connection clone "$con" "$newname" >/dev/null 2>&1; then
    nmcli connection modify "$newname" connection.autoconnect yes \
          connection.autoconnect-priority 100 >/dev/null 2>&1
    log "  cloned active WiFi '$con' -> persistent profile '$newname' (autoconnect on)"
    log "  saved: /etc/NetworkManager/system-connections/${newname}.nmconnection"
    return 0
  fi

  log "  FAILED to persist WiFi '$con' — refusing to disable cloud-init"
  return 1
}

log "[1] cloud-init"
if [ -d /etc/cloud ]; then
  if [ -e /etc/cloud/cloud-init.disabled ]; then
    log "  already disabled"
  elif preserve_active_wifi; then
    touch /etc/cloud/cloud-init.disabled
    log "  disabled (created /etc/cloud/cloud-init.disabled)"
    log "  NOTE: re-flash the card if you ever want cloud-init provisioning again"
  else
    log "  SKIPPED disabling cloud-init to avoid a WiFi lock-out."
    log "  Set up a persistent NetworkManager WiFi profile first, e.g.:"
    log "    sudo nmcli device wifi connect \"YOUR_SSID\" password \"YOUR_PASSWORD\""
    log "  then re-run this script."
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