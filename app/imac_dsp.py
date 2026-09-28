#!/usr/bin/python3
"""Machine profiles and PipeWire filter-chain generation for iMac DSP Control.

Usable without GTK so the installer can call it:

    imac_dsp.py detect        print the detected profile as key=value lines
    imac_dsp.py write-config  save the detected profile and write the DSP config
"""

import json
import sys
from pathlib import Path


CONFIG_DIR = Path.home() / ".config" / "imac-dsp-control"
SETTINGS_FILE = CONFIG_DIR / "settings.json"
PROFILE_FILE = CONFIG_DIR / "profile.json"
DSP_FILE = Path.home() / ".config" / "pipewire" / "filter-chain.conf.d" / "imac-dsp.conf"

CS4208 = "0x10134208"
CS8409 = "0x10138409"
CODEC_NAMES = {CS4208: "CS4208", CS8409: "CS8409"}

# crossover-4.0: the codec exposes four channels, FL/FR tweeters and RL/RR
#   woofers; the DSP performs the crossover.
# stereo-2.0: the codec exposes stereo and the driver/amplifiers feed tweeter
#   and woofer of each side; the DSP only protects and shapes the full range.
LAYOUTS = {
    "crossover-4.0": dict(channels=4, positions="FL FR RL RR", sink_profile="analog-surround-40"),
    "stereo-2.0": dict(channels=2, positions="FL FR", sink_profile="analog-stereo"),
}

MODELS = {
    "iMac16,2": dict(description="iMac 21.5-inch, Late 2015", codec=CS4208,
                     layout="crossover-4.0", min_protection=35.0),
    "iMac18,1": dict(description="iMac 21.5-inch, 2017", codec=CS8409,
                     layout="stereo-2.0", min_protection=60.0),
    "iMac18,2": dict(description="iMac 21.5-inch Retina 4K, 2017", codec=CS8409,
                     layout="stereo-2.0", min_protection=60.0),
    "iMac18,3": dict(description="iMac 27-inch Retina 5K, 2017", codec=CS8409,
                     layout="stereo-2.0", min_protection=50.0),
    "iMac19,1": dict(description="iMac 27-inch Retina 5K, 2019", codec=CS8409,
                     layout="stereo-2.0", min_protection=50.0),
    "iMac19,2": dict(description="iMac 21.5-inch Retina 4K, 2019", codec=CS8409,
                     layout="stereo-2.0", min_protection=60.0),
}

# Profile used by installations made before profiles existed (iMac16,2 only).
LEGACY_PCI = "pci-0000_00_1b.0"

# Bass shelf corner used by the stereo layout instead of a crossover.
BASS_SHELF = 150.0
TREBLE_SHELF = 6500.0

DEFAULTS = {
    "preset": "Balanced",
    "crossover": 350.0,
    "protection": 45.0,
    "woofer_gain": 0.0,
    "treble_gain": -1.0,
    "headroom": -1.0,
    "dsp_volume": 100.0,
    "hardware_volume": 100.0,
}


class ProfileError(Exception):
    pass


def product_name():
    try:
        return Path("/sys/class/dmi/id/product_name").read_text().strip()
    except OSError:
        return ""


def find_codec_card(vendor_id):
    """Return the ALSA card directory name (cardN) holding the given codec."""
    for codec in sorted(Path("/proc/asound").glob("card*/codec#*")):
        try:
            text = codec.read_text(errors="replace")
        except OSError:
            continue
        for line in text.splitlines():
            if line.startswith("Vendor Id:") and line.split(":", 1)[1].strip().lower() == vendor_id:
                return codec.parent.name
    return None


def card_pci_name(card):
    """Return the PipeWire/UCM style bus name, e.g. pci-0000_00_1f.3."""
    device = Path("/sys/class/sound") / card / "device"
    if not device.exists():
        return None
    address = device.resolve().name
    if address.count(":") != 2:
        return None
    return "pci-" + address.replace(":", "_")


def make_profile(product, pci):
    model = MODELS[product]
    layout = LAYOUTS[model["layout"]]
    return dict(
        product=product,
        description=model["description"],
        codec=model["codec"],
        layout=model["layout"],
        channels=layout["channels"],
        positions=layout["positions"],
        min_protection=model["min_protection"],
        pci=pci,
        device="alsa_card." + pci,
        sink="alsa_output.%s.%s" % (pci, layout["sink_profile"]),
    )


def detect_profile():
    product = product_name()
    model = MODELS.get(product)
    if model is None:
        raise ProfileError(
            "Unsupported machine %r. Supported: %s." % (product, ", ".join(MODELS)))
    card = find_codec_card(model["codec"])
    if card is None:
        raise ProfileError(
            "%s detected, but no ALSA card exposes codec %s (%s)."
            % (product, model["codec"], CODEC_NAMES[model["codec"]]))
    pci = card_pci_name(card)
    if pci is None:
        raise ProfileError("Could not resolve the PCI address of ALSA %s." % card)
    return make_profile(product, pci)


def load_profile():
    try:
        profile = json.loads(PROFILE_FILE.read_text())
        if profile.get("layout") in LAYOUTS:
            return profile
    except (OSError, json.JSONDecodeError):
        pass
    return make_profile("iMac16,2", LEGACY_PCI)


def save_profile(profile):
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    PROFILE_FILE.write_text(json.dumps(profile, indent=2) + "\n")


def load_settings():
    values = DEFAULTS.copy()
    try:
        values.update(json.loads(SETTINGS_FILE.read_text()))
    except (OSError, json.JSONDecodeError):
        pass
    return values


def filter_list(filters):
    return "\n".join(
        "                { type = %s freq = %s%s%s }" % (
            kind,
            f"{freq:g}",
            "" if gain is None else f" gain = {gain:g}",
            "" if freq == 0 else " q = 0.7071",
        )
        for kind, freq, gain in filters
    )


def _crossover_graph(values, protection):
    crossover = float(values["crossover"])
    headroom = float(values["headroom"])
    woofer_level = headroom + float(values["woofer_gain"])
    treble = float(values["treble_gain"])

    tweeter = filter_list([
        ("bq_highshelf", 0, headroom),
        ("bq_highpass", crossover, None),
        ("bq_highpass", crossover, None),
        ("bq_highshelf", TREBLE_SHELF, treble),
    ])
    woofer = filter_list([
        ("bq_highshelf", 0, woofer_level),
        ("bq_highpass", protection, None),
        ("bq_highpass", protection, None),
        ("bq_lowpass", crossover, None),
        ("bq_lowpass", crossover, None),
    ])
    return f'''        nodes = [
          {{ type = builtin name = copyL label = copy }}
          {{ type = builtin name = copyR label = copy }}
          {{ type = builtin name = crossover label = param_eq
            config = {{
              filters1 = [
{tweeter}
              ]
              filters2 = [
{tweeter}
              ]
              filters3 = [
{woofer}
              ]
              filters4 = [
{woofer}
              ]
            }}
          }}
        ]
        links = [
          {{ output = "copyL:Out" input = "crossover:In 1" }}
          {{ output = "copyR:Out" input = "crossover:In 2" }}
          {{ output = "copyL:Out" input = "crossover:In 3" }}
          {{ output = "copyR:Out" input = "crossover:In 4" }}
        ]
        inputs = [ "copyL:In" "copyR:In" ]
        outputs = [ "crossover:Out 1" "crossover:Out 2" "crossover:Out 3" "crossover:Out 4" ]'''


def _stereo_graph(values, protection):
    full_range = filter_list([
        ("bq_highshelf", 0, float(values["headroom"])),
        ("bq_highpass", protection, None),
        ("bq_highpass", protection, None),
        ("bq_lowshelf", BASS_SHELF, float(values["woofer_gain"])),
        ("bq_highshelf", TREBLE_SHELF, float(values["treble_gain"])),
    ])
    return f'''        nodes = [
          {{ type = builtin name = eq label = param_eq
            config = {{
              filters1 = [
{full_range}
              ]
              filters2 = [
{full_range}
              ]
            }}
          }}
        ]
        inputs = [ "eq:In 1" "eq:In 2" ]
        outputs = [ "eq:Out 1" "eq:Out 2" ]'''


def make_dsp_config(values, profile):
    protection = max(float(values["protection"]), float(profile["min_protection"]))
    if profile["layout"] == "crossover-4.0":
        graph = _crossover_graph(values, protection)
        summary = "stereo input -> FL/FR tweeters + RL/RR woofers"
    else:
        graph = _stereo_graph(values, protection)
        summary = "full-range stereo, tweeter/woofer split by the driver"
    return f'''# Generated by iMac DSP Control for {profile["product"]}: {summary}.
# Manual edits may be overwritten.
context.modules = [
  {{ name = libpipewire-module-filter-chain
    args = {{
      node.description = "iMac DSP"
      media.name = "iMac DSP"
      filter.graph = {{
{graph}
      }}
      capture.props = {{
        node.name = "imac_dsp"
        node.description = "iMac DSP"
        media.class = "Audio/Sink"
        audio.channels = 2
        audio.position = [ FL FR ]
      }}
      playback.props = {{
        node.name = "imac_dsp_output"
        node.description = "iMac DSP output"
        node.target = "{profile["sink"]}"
        node.passive = true
        stream.dont-remix = true
        audio.channels = {profile["channels"]}
        audio.position = [ {profile["positions"]} ]
      }}
    }}
  }}
]
'''


def write_dsp_config(values, profile):
    DSP_FILE.parent.mkdir(parents=True, exist_ok=True)
    DSP_FILE.write_text(make_dsp_config(values, profile))


def main(argv):
    command = argv[1] if len(argv) > 1 else ""
    if command not in {"detect", "write-config"}:
        print("usage: imac_dsp.py detect|write-config", file=sys.stderr)
        return 2
    try:
        profile = detect_profile()
    except ProfileError as error:
        print(error, file=sys.stderr)
        return 1
    if command == "detect":
        for key, value in profile.items():
            print(f"{key}={value}")
        return 0
    save_profile(profile)
    write_dsp_config(load_settings(), profile)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
