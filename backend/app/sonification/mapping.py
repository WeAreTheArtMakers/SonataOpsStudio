from __future__ import annotations

from typing import Any

from app.sonification.presets import resolve_preset


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def map_features_to_control_curves(
    metric_name: str,
    features: dict[str, Any],
    preset_name: str,
) -> dict[str, Any]:
    preset = resolve_preset(preset_name)
    trend = float(features.get("trend", 0.0))
    volatility = float(features.get("volatility", 0.2))
    severity = float(features.get("severity", 20.0))
    confidence = float(features.get("confidence", 0.6))

    tempo = int(round(clamp(60 + volatility * 110, 60, 140)))
    pitch_center = preset["base_freq"] + (trend * preset["pitch_span"])
    pitch_secondary = pitch_center * (1.5 if trend >= 0 else 1.333)

    brightness_signal = float(features.get("control_signal", 0.5))
    if metric_name.lower() == "traffic":
        brightness_signal = clamp(0.35 + volatility * 1.2, 0.0, 1.0)
    if metric_name.lower() == "riskscore":
        brightness_signal = clamp(0.4 + severity / 100, 0.0, 1.0)

    transients = clamp((severity / 100) * preset["transient_gain"], 0.01, 0.35)
    stereo_width = clamp((confidence * 0.8) + preset["width_bias"], 0.1, 0.95)
    brightness = clamp((brightness_signal * 0.7) + preset["brightness_bias"], 0.1, 1.0)

    return {
        "tempo_bpm": tempo,
        "pitch_center_hz": round(pitch_center, 4),
        "pitch_secondary_hz": round(pitch_secondary, 4),
        "transient_gain": round(transients, 4),
        "brightness": round(brightness, 4),
        "stereo_width": round(stereo_width, 4),
        "severity": int(severity),
    }
