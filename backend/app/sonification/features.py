from __future__ import annotations

import math
from statistics import mean, median, pstdev
from typing import Any


def _rolling_mean(values: list[float], index: int, window: int = 10) -> float:
    start = max(0, index - window + 1)
    sample = values[start : index + 1]
    return sum(sample) / len(sample)


def _linear_slope(values: list[float]) -> float:
    n = len(values)
    if n < 2:
        return 0.0
    x_mean = (n - 1) / 2
    y_mean = sum(values) / n
    numerator = sum((i - x_mean) * (v - y_mean) for i, v in enumerate(values))
    denominator = sum((i - x_mean) ** 2 for i in range(n)) or 1.0
    return numerator / denominator


def compute_anomaly_features(
    values: list[float],
    severity_hint: int | None = None,
) -> dict[str, Any]:
    if len(values) < 8:
        return {
            "trend": 0.0,
            "volatility": 0.0,
            "residual": 0.0,
            "robust_z": 0.0,
            "change_point": 0.0,
            "confidence": 0.5,
            "severity": severity_hint or 0,
        }

    med = median(values)
    deviations = [abs(v - med) for v in values]
    mad = median(deviations) or 1e-6
    robust_z = abs((values[-1] - med) / (1.4826 * mad + 1e-6))

    residuals = [v - _rolling_mean(values, idx, window=12) for idx, v in enumerate(values)]
    residual_mu = mean(residuals)
    residual_sigma = pstdev(residuals) or 1e-6
    residual_z = abs((residuals[-1] - residual_mu) / residual_sigma)

    recent = values[-20:] if len(values) >= 20 else values
    level = abs(mean(recent)) + 1e-6
    volatility = (pstdev(recent) or 0.0) / level

    trend = _linear_slope(values[-30:] if len(values) >= 30 else values)
    trend_norm = max(-1.0, min(1.0, trend / (level / 12 + 1e-6)))

    change_point = abs(values[-1] - values[-2]) / ((pstdev(recent) or 1.0) + 1e-6)
    confidence = max(0.05, min(1.0, 1.0 - min(volatility, 1.0) * 0.7))

    severity = severity_hint
    if severity is None:
        severity = int(max(0.0, min(100.0, (robust_z * 24) + (residual_z * 20) + (change_point * 14) + (volatility * 45))))

    return {
        "trend": float(trend_norm),
        "volatility": float(volatility),
        "residual": float(residual_z),
        "robust_z": float(robust_z),
        "change_point": float(change_point),
        "confidence": float(confidence),
        "severity": int(severity),
    }


def feature_frame_from_points(points: list[tuple[object, float]]) -> dict[str, Any]:
    values = [float(v) for _, v in points]
    return compute_anomaly_features(values)
