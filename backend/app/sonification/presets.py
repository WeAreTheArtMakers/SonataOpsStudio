PRESETS: dict[str, dict[str, float]] = {
    "Executive Minimal": {
        "base_freq": 220.0,
        "pitch_span": 42.0,
        "transient_gain": 0.06,
        "brightness_bias": 0.34,
        "width_bias": 0.28,
        "third_ratio": 1.2599,
        "fifth_ratio": 1.4983,
        "default_intensity": 0.42,
        "default_glitch": 0.08,
        "default_harmonizer": 0.30,
        "default_pad_depth": 0.58,
        "default_ambient_mix": 0.36,
        "default_rhythm_density": 0.92,
        "tempo_bias": -4.0,
    },
    "Risk Tension": {
        "base_freq": 174.0,
        "pitch_span": 60.0,
        "transient_gain": 0.20,
        "brightness_bias": 0.58,
        "width_bias": 0.33,
        "third_ratio": 1.1892,
        "fifth_ratio": 1.4983,
        "default_intensity": 0.66,
        "default_glitch": 0.42,
        "default_harmonizer": 0.48,
        "default_pad_depth": 0.52,
        "default_ambient_mix": 0.40,
        "default_rhythm_density": 1.22,
        "tempo_bias": 6.0,
    },
    "Growth Momentum": {
        "base_freq": 247.0,
        "pitch_span": 68.0,
        "transient_gain": 0.14,
        "brightness_bias": 0.50,
        "width_bias": 0.44,
        "third_ratio": 1.2599,
        "fifth_ratio": 1.4983,
        "default_intensity": 0.56,
        "default_glitch": 0.18,
        "default_harmonizer": 0.52,
        "default_pad_depth": 0.62,
        "default_ambient_mix": 0.46,
        "default_rhythm_density": 1.28,
        "tempo_bias": 8.0,
    },
    "modART": {
        "base_freq": 207.65,
        "pitch_span": 36.0,
        "transient_gain": 0.10,
        "brightness_bias": 0.43,
        "width_bias": 0.62,
        "third_ratio": 1.3348,
        "fifth_ratio": 1.4983,
        "default_intensity": 0.54,
        "default_glitch": 0.22,
        "default_harmonizer": 0.66,
        "default_pad_depth": 0.90,
        "default_ambient_mix": 0.86,
        "default_rhythm_density": 1.08,
        "tempo_bias": -6.0,
    },
    "Glitch Harmonics": {
        "base_freq": 196.0,
        "pitch_span": 74.0,
        "transient_gain": 0.30,
        "brightness_bias": 0.70,
        "width_bias": 0.52,
        "third_ratio": 1.1892,
        "fifth_ratio": 1.4983,
        "default_intensity": 0.82,
        "default_glitch": 0.76,
        "default_harmonizer": 0.74,
        "default_pad_depth": 0.46,
        "default_ambient_mix": 0.40,
        "default_rhythm_density": 1.56,
        "tempo_bias": 14.0,
    },
    "Ambient Boardroom": {
        "base_freq": 233.08,
        "pitch_span": 28.0,
        "transient_gain": 0.05,
        "brightness_bias": 0.30,
        "width_bias": 0.56,
        "third_ratio": 1.2599,
        "fifth_ratio": 1.4983,
        "default_intensity": 0.36,
        "default_glitch": 0.05,
        "default_harmonizer": 0.56,
        "default_pad_depth": 0.94,
        "default_ambient_mix": 0.80,
        "default_rhythm_density": 0.82,
        "tempo_bias": -10.0,
    },
    "Incident Grid": {
        "base_freq": 164.81,
        "pitch_span": 78.0,
        "transient_gain": 0.32,
        "brightness_bias": 0.72,
        "width_bias": 0.46,
        "third_ratio": 1.1892,
        "fifth_ratio": 1.4983,
        "default_intensity": 0.86,
        "default_glitch": 0.84,
        "default_harmonizer": 0.64,
        "default_pad_depth": 0.44,
        "default_ambient_mix": 0.36,
        "default_rhythm_density": 1.78,
        "tempo_bias": 16.0,
    },
    "Clean Harmonics": {
        "base_freq": 246.94,
        "pitch_span": 34.0,
        "transient_gain": 0.07,
        "brightness_bias": 0.40,
        "width_bias": 0.60,
        "third_ratio": 1.2599,
        "fifth_ratio": 1.4983,
        "default_intensity": 0.44,
        "default_glitch": 0.04,
        "default_harmonizer": 0.84,
        "default_pad_depth": 0.82,
        "default_ambient_mix": 0.56,
        "default_rhythm_density": 0.94,
        "tempo_bias": -2.0,
    },
    "Pulse Relay": {
        "base_freq": 184.99,
        "pitch_span": 54.0,
        "transient_gain": 0.22,
        "brightness_bias": 0.54,
        "width_bias": 0.40,
        "third_ratio": 1.2599,
        "fifth_ratio": 1.4983,
        "default_intensity": 0.70,
        "default_glitch": 0.36,
        "default_harmonizer": 0.58,
        "default_pad_depth": 0.48,
        "default_ambient_mix": 0.34,
        "default_rhythm_density": 1.44,
        "tempo_bias": 10.0,
    },
}


LEGACY_PRESET_ALIASES: dict[str, str] = {
    "state azure": "modART",
    "state_azure": "modART",
    "state-azure": "modART",
}


def normalize_preset_name(name: str) -> str:
    cleaned = (name or "").strip()
    if not cleaned:
        return "Executive Minimal"

    if cleaned in PRESETS:
        return cleaned

    lowered = cleaned.lower()
    for preset_name in PRESETS:
        if preset_name.lower() == lowered:
            return preset_name

    return LEGACY_PRESET_ALIASES.get(lowered, cleaned)


def resolve_preset(name: str) -> dict[str, float]:
    return PRESETS.get(normalize_preset_name(name), PRESETS["Executive Minimal"])
