#!/bin/sh
set -eu

sudo rm -f -- /etc/modprobe.d/imac16-2-audio.conf
sudo rm -f -- /lib/firmware/hda-imac-cs4208.fw
rm -f -- "$HOME/.config/wireplumber/wireplumber.conf.d/90-imac-surround.conf"
rm -f -- "$HOME/.config/pipewire/filter-chain.conf.d/imac-dsp.conf"
rm -f -- "$HOME/.config/imac-dsp-control/profile.json"
rm -f -- "$HOME/.local/bin/imac-dsp-control"
rm -f -- "$HOME/.local/share/applications/imac-dsp-control.desktop"
rm -f -- "$HOME/.local/lib/imac-dsp-control/imac-dsp-control"
rm -f -- "$HOME/.local/lib/imac-dsp-control/imac_dsp.py"
rm -rf -- "$HOME/.local/lib/imac-dsp-control/__pycache__"
systemctl --user restart wireplumber.service filter-chain.service

printf '%s\n' 'Removed package files. Reboot to unload the HDA patch.'
