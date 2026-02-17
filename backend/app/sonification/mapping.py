from __future__ import annotations

from typing import Any

from app.sonification.presets import resolve_preset


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def derive_anomaly_mode(features: dict[str, Any], severity: float) -> str:
    residual = float(features.get("residual", 0.0))
    robust_z = float(features.get("robust_z", 0.0))
    change_point = float(features.get("change_point", 0.0))

    if severity >= 68.0 or residual >= 2.6 or robust_z >= 2.8 or change_point >= 2.4:
        return "incident"
    if severity <= 45.0 and residual <= 2.0 and robust_z <= 2.0 and change_point <= 1.8:
        return "stable"
    return "watch"


def map_features_to_control_curves(
    metric_name: str,
    features: dict[str, Any],
    preset_name: str,
    overrides: dict[str, float] | None = None,
) -> dict[str, Any]:
    overrides = overrides or {}
    preset = resolve_preset(preset_name)
    trend = float(features.get("trend", 0.0))
    volatility = float(features.get("volatility", 0.2))
    severity = float(features.get("severity", 20.0))
    confidence = float(features.get("confidence", 0.6))
    anomaly_mode = derive_anomaly_mode(features, severity)

    tempo_min = int(round(clamp(float(overrides.get("tempo_min", 60.0)), 40.0, 180.0)))
    tempo_max = int(round(clamp(float(overrides.get("tempo_max", 140.0)), 50.0, 200.0)))
    if tempo_max <= tempo_min:
        tempo_max = tempo_min + 10

    tempo_bias = float(preset.get("tempo_bias", 0.0))
    tempo_unclamped = 66.0 + (volatility * 90.0) + (severity * 0.16) + tempo_bias
    tempo = int(round(clamp(tempo_unclamped, float(tempo_min), float(tempo_max))))

    pitch_center = preset["base_freq"] + (trend * preset["pitch_span"])
    pitch_secondary = pitch_center * (1.3348 if trend < 0 else 1.4983)
    harmonic_third = pitch_center * float(preset.get("third_ratio", 1.2599))
    harmonic_fifth = pitch_center * float(preset.get("fifth_ratio", 1.4983))

    brightness_signal = float(features.get("control_signal", 0.5))
    if metric_name.lower() == "traffic":
        brightness_signal = clamp(0.35 + volatility * 1.2, 0.0, 1.0)
    if metric_name.lower() == "riskscore":
        brightness_signal = clamp(0.4 + severity / 100, 0.0, 1.0)

    intensity_default = float(preset.get("default_intensity", 0.5)) + (severity / 320.0)
    intensity = clamp(float(overrides.get("intensity", intensity_default)), 0.1, 1.0)

    glitch_default = float(preset.get("default_glitch", 0.1)) + (severity / 300.0)
    glitch_density = clamp(float(overrides.get("glitch_density", glitch_default)), 0.0, 1.0)

    harmonizer_default = float(preset.get("default_harmonizer", 0.45)) + (abs(trend) * 0.2)
    harmonizer_mix = clamp(float(overrides.get("harmonizer_mix", harmonizer_default)), 0.0, 1.0)

    pad_default = float(preset.get("default_pad_depth", 0.6)) + ((1.0 - confidence) * 0.2)
    pad_depth = clamp(float(overrides.get("pad_depth", pad_default)), 0.1, 1.0)

    ambient_default = float(preset.get("default_ambient_mix", 0.4)) + (volatility * 0.15)
    ambient_mix = clamp(float(overrides.get("ambient_mix", ambient_default)), 0.0, 1.0)

    rhythm_default = float(preset.get("default_rhythm_density", 1.0)) + (volatility * 0.35) + (severity / 280.0)
    rhythm_density = clamp(float(overrides.get("rhythm_density", rhythm_default)), 0.7, 2.2)

    if anomaly_mode == "incident":
        glitch_density = clamp(max(glitch_density, 0.56 + (severity / 240.0) + (volatility * 0.15)), 0.0, 1.0)
        rhythm_density = clamp(max(rhythm_density, 1.2 + (severity / 180.0)), 0.7, 2.2)
        harmonizer_mix = clamp(max(harmonizer_mix, 0.50), 0.0, 1.0)
        ambient_mix = clamp(min(ambient_mix, 0.64), 0.0, 1.0)
    elif anomaly_mode == "stable":
        glitch_density = clamp(min(glitch_density, 0.16 + (volatility * 0.2)), 0.0, 1.0)
        harmonizer_mix = clamp(max(harmonizer_mix, 0.60 + ((1.0 - confidence) * 0.12)), 0.0, 1.0)
        rhythm_density = clamp(min(rhythm_density, 1.08), 0.7, 2.2)
        ambient_mix = clamp(max(ambient_mix, 0.44), 0.0, 1.0)

    transients = clamp(
        (severity / 100) * preset["transient_gain"] * (0.7 + intensity * 0.7) * (0.7 + rhythm_density * 0.35),
        0.01,
        0.45,
    )
    stereo_width = clamp((confidence * 0.8) + preset["width_bias"], 0.1, 0.95)
    brightness = clamp((brightness_signal * 0.7) + preset["brightness_bias"], 0.1, 1.0)

    return {
        "anomaly_mode": anomaly_mode,
        "tempo_bpm": tempo,
        "tempo_min": tempo_min,
        "tempo_max": tempo_max,
        "pitch_center_hz": round(pitch_center, 4),
        "pitch_secondary_hz": round(pitch_secondary, 4),
        "harmonic_third_hz": round(harmonic_third, 4),
        "harmonic_fifth_hz": round(harmonic_fifth, 4),
        "transient_gain": round(transients, 4),
        "brightness": round(brightness, 4),
        "stereo_width": round(stereo_width, 4),
        "intensity": round(intensity, 4),
        "glitch_density": round(glitch_density, 4),
        "harmonizer_mix": round(harmonizer_mix, 4),
        "pad_depth": round(pad_depth, 4),
        "ambient_mix": round(ambient_mix, 4),
        "rhythm_density": round(rhythm_density, 4),
        "severity": int(severity),
    }
