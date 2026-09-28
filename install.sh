#!/bin/sh
set -eu

PACKAGE_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)

for command_name in python3 wpctl pw-dump systemctl sudo install sed; do
    command -v "$command_name" >/dev/null 2>&1 || {
        printf 'Missing required command: %s\n' "$command_name" >&2
        exit 1
    }
done

# Refuses unsupported machines, or a supported machine without its codec.
PROFILE_INFO=$(python3 "$PACKAGE_DIR/app/imac_dsp.py" detect) || {
    printf '%s\n' 'Refusing installation.' >&2
    exit 1
}
profile_value() {
    printf '%s\n' "$PROFILE_INFO" | sed -n "s/^$1=//p"
}
PRODUCT=$(profile_value product)
LAYOUT=$(profile_value layout)
PCI=$(profile_value pci)
printf 'Detected %s (%s), layout %s, card %s.\n' \
    "$(profile_value description)" "$PRODUCT" "$LAYOUT" "$PCI"

if [ "$LAYOUT" = stereo-2.0 ]; then
    # The in-kernel CS8409 driver only initialises Dell hardware; Apple
    # speaker amplifiers need an out-of-tree (DKMS) build of the module.
    MODULE_PATH=$(PATH="$PATH:/usr/sbin:/sbin" modinfo -n snd-hda-codec-cs8409 2>/dev/null || true)
    case "$MODULE_PATH" in
        */updates/*|*/extra/*) ;;
        *)
            printf '%s\n' \
                'Warning: no out-of-tree snd-hda-codec-cs8409 module found.' \
                'The internal speakers stay silent until an Apple-capable CS8409' \
                'driver is installed; the DSP is installed anyway.' >&2
            ;;
    esac
fi

STAMP=$(date +%Y%m%d-%H%M%S)
backup_file() {
    target=$1
    if [ -e "$target" ]; then
        sudo cp -a -- "$target" "$target.backup-$STAMP"
    fi
}

WIREPLUMBER_CONF="$HOME/.config/wireplumber/wireplumber.conf.d/90-imac-surround.conf"

if [ "$LAYOUT" = crossover-4.0 ]; then
    backup_file /lib/firmware/hda-imac-cs4208.fw
    backup_file /etc/modprobe.d/imac16-2-audio.conf

    sudo install -m 0644 "$PACKAGE_DIR/firmware/hda-imac-cs4208.fw" /lib/firmware/hda-imac-cs4208.fw
    sudo install -m 0644 "$PACKAGE_DIR/modprobe.d/imac16-2-audio.conf" /etc/modprobe.d/imac16-2-audio.conf

    mkdir -p "$HOME/.config/wireplumber/wireplumber.conf.d"
    sed "s/@PCI@/$PCI/g" \
        "$PACKAGE_DIR/config/wireplumber/wireplumber.conf.d/90-imac-surround.conf" \
        > "$WIREPLUMBER_CONF"
    chmod 0644 "$WIREPLUMBER_CONF"
else
    rm -f -- "$WIREPLUMBER_CONF"
fi

mkdir -p "$HOME/.local/lib/imac-dsp-control"
mkdir -p "$HOME/.local/bin"
mkdir -p "$HOME/.local/share/applications"
install -m 0755 "$PACKAGE_DIR/app/imac-dsp-control" \
    "$HOME/.local/lib/imac-dsp-control/imac-dsp-control"
install -m 0755 "$PACKAGE_DIR/app/imac_dsp.py" \
    "$HOME/.local/lib/imac-dsp-control/imac_dsp.py"
ln -sf "$HOME/.local/lib/imac-dsp-control/imac-dsp-control" \
    "$HOME/.local/bin/imac-dsp-control"
install -m 0644 "$PACKAGE_DIR/share/applications/imac-dsp-control.desktop" \
    "$HOME/.local/share/applications/imac-dsp-control.desktop"

# Saves the machine profile and generates the PipeWire DSP from it,
# keeping any tuning already saved by the control panel.
python3 "$HOME/.local/lib/imac-dsp-control/imac_dsp.py" write-config

systemctl --user enable filter-chain.service

printf '%s\n' 'Installed. Reboot, then launch iMac DSP Control from the application menu.'
