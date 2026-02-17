PRESETS: dict[str, dict[str, float]] = {
    "Executive Minimal": {
        "base_freq": 220.0,
        "pitch_span": 48.0,
        "transient_gain": 0.06,
        "brightness_bias": 0.35,
        "width_bias": 0.25,
    },
    "Risk Tension": {
        "base_freq": 174.0,
        "pitch_span": 62.0,
        "transient_gain": 0.18,
        "brightness_bias": 0.55,
        "width_bias": 0.32,
    },
    "Growth Momentum": {
        "base_freq": 247.0,
        "pitch_span": 70.0,
        "transient_gain": 0.12,
        "brightness_bias": 0.48,
        "width_bias": 0.42,
    },
}


def resolve_preset(name: str) -> dict[str, float]:
    return PRESETS.get(name, PRESETS["Executive Minimal"])
