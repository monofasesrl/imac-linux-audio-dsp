# iMac Linux audio DSP

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

Speaker routing and a conservative software DSP for Intel iMacs running
Linux with PipeWire.

## Supported models

| DMI product | Model                          | Codec  | Layout          |
|-------------|--------------------------------|--------|-----------------|
| `iMac16,2`  | iMac 21.5-inch, Late 2015      | CS4208 | 4.0 crossover   |
| `iMac18,1`  | iMac 21.5-inch, 2017           | CS8409 | stereo          |
| `iMac18,2`  | iMac 21.5-inch Retina 4K, 2017 | CS8409 | stereo          |
| `iMac18,3`  | iMac 27-inch Retina 5K, 2017   | CS8409 | stereo          |
| `iMac19,1`  | iMac 27-inch Retina 5K, 2019   | CS8409 | stereo          |
| `iMac19,2`  | iMac 21.5-inch Retina 4K, 2019 | CS8409 | stereo          |

Apple did not release a new non-Retina 21.5-inch iMac in 2019; the 2017
`iMac18,1` stayed on sale and is covered above.

### iMac16,2 (4.0 crossover)

An HDA firmware patch exposes the four amplifier channels. The stereo input is
split into:

- FL/FR: left and right tweeters, fourth-order high-pass at 350 Hz;
- RL/RR: left and right woofers, fourth-order low-pass at 350 Hz;
- woofer protection: fourth-order high-pass at 45 Hz;
- DSP headroom: -1 dB;
- slight treble trim: -1 dB above 6.5 kHz.

### iMac 2017 and 2019 (stereo)

These models use a Cirrus Logic CS8409 bridge with separate speaker
amplifiers. The CS8409 driver shipped with the kernel only initialises Dell
hardware, so the internal speakers are silent until an Apple-capable,
out-of-tree `snd-hda-codec-cs8409` module (usually DKMS) is installed. That
driver exposes a stereo output and feeds the tweeter and woofer of each side
itself, so this package does **not** apply a crossover or install any HDA
patch on these models. The DSP only:

- removes sub-bass with a fourth-order high-pass (default and minimum 60 Hz
  on 21.5-inch, 50 Hz on 27-inch models);
- applies a bass low shelf below 150 Hz (the control panel's *Bass level*);
- applies headroom (-1 dB) and a treble shelf above 6.5 kHz (-1 dB).

The installer warns if no out-of-tree CS8409 module is found.

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

The installer checks the DMI product name against the table above and
requires the ALSA card holding the expected codec (`10134208` for CS4208,
`10138409` for CS8409). The PipeWire sink name is derived from that card's
PCI address, and the detected profile is saved in
`~/.config/imac-dsp-control/profile.json`. It requires PipeWire, WirePlumber,
`wpctl`, and the systemd user service `filter-chain.service`.

The tuning approximates the type of crossover and protection used by macOS;
it is not Apple's proprietary DSP calibration.

## Supporting other Macs

Profiles live in `app/imac_dsp.py` (`MODELS`). Support for another Mac
requires a tested profile describing its DMI product name, codec ID, ALSA
channel order, speaker roles, safe crossover, protection frequency and gain
limits. Do not reuse the iMac16,2 firmware patch or tuning blindly:
incorrect routing can send low frequencies to tweeters and damage them.

Contributions with verified channel maps and conservative measurements are
welcome. Each new model should have its own profile and an explicit hardware
compatibility check.

## Graphical control panel

The package installs **iMac DSP Control** in the desktop application menu. It
provides live DSP and hardware volume controls, four presets, crossover
(iMac16,2 only) and woofer-protection frequencies, woofer/bass and treble
trim, headroom, DSP/direct output switching, and a safe left/right test. Press **Apply** to save tuning and
reload the filter. Custom settings are stored in
`~/.config/imac-dsp-control/settings.json`.
