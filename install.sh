#!/bin/sh
set -eu

PACKAGE_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
PRODUCT=$(cat /sys/class/dmi/id/product_name 2>/dev/null || true)

if [ "$PRODUCT" != "iMac16,2" ]; then
    printf 'Refusing installation: detected %s, expected iMac16,2.\n' "$PRODUCT" >&2
    exit 1
fi

for command_name in python3 wpctl pw-dump systemctl sudo install; do
    command -v "$command_name" >/dev/null 2>&1 || {
        printf 'Missing required command: %s\n' "$command_name" >&2
        exit 1
    }
done

STAMP=$(date +%Y%m%d-%H%M%S)
backup_file() {
    target=$1
    if [ -e "$target" ]; then
        sudo cp -a -- "$target" "$target.backup-$STAMP"
    fi
}

backup_file /lib/firmware/hda-imac-cs4208.fw
backup_file /etc/modprobe.d/imac16-2-audio.conf

sudo install -m 0644 "$PACKAGE_DIR/firmware/hda-imac-cs4208.fw" /lib/firmware/hda-imac-cs4208.fw
sudo install -m 0644 "$PACKAGE_DIR/modprobe.d/imac16-2-audio.conf" /etc/modprobe.d/imac16-2-audio.conf

mkdir -p "$HOME/.config/wireplumber/wireplumber.conf.d"
mkdir -p "$HOME/.config/pipewire/filter-chain.conf.d"
install -m 0644 "$PACKAGE_DIR/config/wireplumber/wireplumber.conf.d/90-imac-surround.conf" \
    "$HOME/.config/wireplumber/wireplumber.conf.d/90-imac-surround.conf"
install -m 0644 "$PACKAGE_DIR/config/pipewire/filter-chain.conf.d/imac-dsp.conf" \
    "$HOME/.config/pipewire/filter-chain.conf.d/imac-dsp.conf"

mkdir -p "$HOME/.local/lib/imac-dsp-control"
mkdir -p "$HOME/.local/bin"
mkdir -p "$HOME/.local/share/applications"
install -m 0755 "$PACKAGE_DIR/app/imac-dsp-control" \
    "$HOME/.local/lib/imac-dsp-control/imac-dsp-control"
ln -sf "$HOME/.local/lib/imac-dsp-control/imac-dsp-control" \
    "$HOME/.local/bin/imac-dsp-control"
install -m 0644 "$PACKAGE_DIR/share/applications/imac-dsp-control.desktop" \
    "$HOME/.local/share/applications/imac-dsp-control.desktop"

systemctl --user enable filter-chain.service

printf '%s\n' 'Installed. Reboot, then launch iMac DSP Control from the application menu.'
