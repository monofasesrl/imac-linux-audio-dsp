# iMac16,2 Linux audio

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

Four-speaker routing and a conservative software DSP for the Cirrus Logic
CS4208 codec used by the 21.5-inch iMac16,2.

The stereo input is split into:

- FL/FR: left and right tweeters, fourth-order high-pass at 350 Hz;
- RL/RR: left and right woofers, fourth-order low-pass at 350 Hz;
- woofer protection: fourth-order high-pass at 45 Hz;
- DSP headroom: -1 dB;
- slight treble trim: -1 dB above 6.5 kHz.

## Install

Run as the desktop user (the script asks for sudo only for system files):

```sh
./install.sh
```

Log out and back in, or reboot. Select `iMac DSP` as the output if it is not
selected automatically. The installer keeps timestamped backups of files it
replaces.

## Remove

```sh
./uninstall.sh
```

Then reboot. Removal deletes only files installed by this package; timestamped
backups are not deleted.

## Compatibility

This package is intentionally restricted to DMI product `iMac16,2` and ALSA
codec `10134208` (CS4208). It requires PipeWire, WirePlumber, `wpctl`, and the
systemd user service `filter-chain.service`.

The tuning approximates the type of crossover and protection used by macOS;
it is not Apple's proprietary DSP calibration.

## Supporting other Macs

The PipeWire DSP and GTK control panel are reusable. Support for another Mac
requires a tested machine profile describing its DMI product name, codec ID,
ALSA channel order, speaker roles, safe crossover, protection frequency and
gain limits. Do not reuse this iMac16,2 firmware patch or tuning blindly:
incorrect routing can send low frequencies to tweeters and damage them.

Contributions with verified channel maps and conservative measurements are
welcome. Each new model should have its own profile and an explicit hardware
compatibility check.

## Graphical control panel

The package installs **iMac DSP Control** in the desktop application menu. It
provides live DSP and hardware volume controls, four presets, crossover and
woofer-protection frequencies, woofer and treble trim, headroom, DSP/direct
4.0 switching, and a safe left/right test. Press **Apply** to save tuning and
reload the filter. Custom settings are stored in
`~/.config/imac-dsp-control/settings.json`.
