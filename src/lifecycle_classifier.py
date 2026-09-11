"""Classify a trend's lifecycle stage from Google Trends time series."""

from dataclasses import dataclass

import numpy as np
import pandas as pd

from src.keyword_generator import LIFECYCLE_STAGES

STAGE_DESCRIPTIONS = {
    "Naciente": (
        "La señal acaba de aparecer y todavía no formó un pico relevante. "
        "Conviene observar si gana persistencia."
    ),
    "Emergente": (
        "El interés acelera ahora desde una presencia todavía acotada. "
        "Es una ventana temprana para explorar y posicionarse."
    ),
    "Crecimiento": (
        "La curva sostiene una subida amplia y se acerca a su máximo. "
        "La adopción sigue expandiéndose."
    ),
    "Masiva": (
        "El interés actual permanece cerca del pico y concentra exposición amplia. "
        "La diferenciación es más difícil."
    ),
    "Saturada": (
        "El interés sigue alto y persistente, pero la curva se estabilizó. "
        "El riesgo de repetición aumenta."
    ),
    "En declive": (
        "El pico quedó atrás y el interés de las últimas 48 horas cayó con claridad. "
        "Conviene evitar activaciones genéricas o buscar una derivación."
    ),
}

STAGE_COLORS = {
    "Naciente": "#6366f1",
    "Emergente": "#22c55e",
    "Crecimiento": "#eab308",
    "Masiva": "#f97316",
    "Saturada": "#ef4444",
    "En declive": "#94a3b8",
}

# The product answers "what is happening right now", so the newest points carry
# most of the weight and the yearly curve only contributes a baseline.
HORIZON_POINTS = {"now": 2, "week": 7, "month": 30}
HORIZON_WEIGHTS = {"now": 0.45, "week": 0.30, "month": 0.18, "year": 0.07}
RECENCY_HALF_LIFE = 4.0

# Decision thresholds, expressed against the observed peak (0-1) unless noted.
MIN_ABSOLUTE_SIGNAL = 5.0
DECLINE_LEVEL = 0.35
MATURE_LEVEL = 0.65
PLATEAU_SHARE = 0.65
NICHE_SHARE = 0.25
RISING_MOMENTUM = 0.05
RISING_ACCELERATION = 0.15


@dataclass
class LifecycleResult:
    stage: str
    confidence: float
    description: str
    metrics: dict
    stage_scores: dict[str, float]


def _aggregate_series(data: pd.DataFrame) -> pd.Series:
    """Sum multiple keyword columns into a single trend signal."""
    if data.shape[1] == 1:
        return data.iloc[:, 0].astype(float)
    return data.sum(axis=1).astype(float)


def _linear_slope(values: np.ndarray) -> float:
    if len(values) < 2:
        return 0.0
    x = np.arange(len(values))
    coeffs = np.polyfit(x, values, 1)
    return float(coeffs[0])


def _clamp01(value: float) -> float:
    return max(0.0, min(float(value), 1.0))


def _smooth(values: np.ndarray) -> np.ndarray:
    """Centered mean that removes one-point noise without erasing a short fad."""
    window = 3 if len(values) >= 14 else 1
    return pd.Series(values).rolling(window, center=True, min_periods=1).mean().values


def _tail_mean(normalized: np.ndarray, points: int) -> float:
    return float(np.mean(normalized[-min(points, len(normalized)) :]))


def _velocity(normalized: np.ndarray, points: int) -> float:
    """Fraction of the peak gained or lost across the window."""
    window = normalized[-min(points, len(normalized)) :]
    if len(window) < 2:
        return 0.0
    return float(_linear_slope(window) * (len(window) - 1))


def _relative_change(current: float, baseline: float) -> float:
    """Acceleration of the current level against a slower baseline."""
    return (current - baseline) / max(baseline, 0.02)


def _recency_weighted_level(normalized: np.ndarray) -> float:
    ages = np.arange(len(normalized))[::-1]
    weights = np.exp(-np.log(2) * ages / RECENCY_HALF_LIFE)
    return float(np.sum(normalized * weights) / np.sum(weights))


def classify_lifecycle(data: pd.DataFrame) -> LifecycleResult:
    """
    Classify one global lifecycle stage weighted towards the present.

    Google Trends values are relative, so every feature is measured against the
    observed peak. Levels are aggregated with exponential recency decay, and the
    stage itself comes from a deterministic ladder so that the label, the curve
    and the projection can never contradict each other.
    """
    series = _aggregate_series(data).dropna()
    values = np.clip(series.values.astype(float), 0, None)
    n = len(values)

    if n < 7:
        raise ValueError("Se necesitan al menos 7 días de datos para clasificar.")

    smoothed = _smooth(values)
    raw_peak = float(np.max(smoothed))
    normalized = smoothed / raw_peak if raw_peak > 0 else np.zeros(n)

    levels = {
        "now": _tail_mean(normalized, HORIZON_POINTS["now"]),
        "week": _tail_mean(normalized, HORIZON_POINTS["week"]),
        "month": _tail_mean(normalized, HORIZON_POINTS["month"]),
        "year": float(np.mean(normalized)),
    }
    weighted_level = sum(HORIZON_WEIGHTS[key] * level for key, level in levels.items())

    # Instantaneous acceleration vs. the slower baselines.
    accel_now = _relative_change(levels["now"], levels["week"])
    accel_week = _relative_change(levels["week"], levels["month"])
    baseline_momentum = _relative_change(levels["month"], levels["year"])

    velocity_week = _velocity(normalized, HORIZON_POINTS["week"])
    velocity_month = _velocity(normalized, HORIZON_POINTS["month"])

    peak_idx = int(np.argmax(normalized))
    peak_age = n - 1 - peak_idx
    persistence = float(np.mean(normalized >= 0.5))
    active_share = float(np.mean(normalized >= 0.1))
    high_share = float(np.mean(normalized[-min(30, n) :] >= 0.7))

    level_now = levels["now"]
    peaked_before = peak_age >= 1
    rising = velocity_month > RISING_MOMENTUM or accel_now > RISING_ACCELERATION
    weak_signal = raw_peak < MIN_ABSOLUTE_SIGNAL

    rising_score = _clamp01(max(velocity_month, accel_now) / 0.3)
    falling_score = _clamp01(-min(velocity_week, accel_now) / 0.3)
    flat_score = 1 - _clamp01(abs(velocity_month) / 0.15)

    scores: dict[str, float] = {
        "Naciente": (
            0.45 * (1 - _clamp01(active_share / 0.3))
            + 0.30 * (1 - _clamp01(raw_peak / 20))
            + 0.25 * (1 - _clamp01(level_now / 0.4))
        ),
        "Emergente": (
            0.45 * rising_score
            + 0.30 * (1 - _clamp01(active_share / 0.3))
            + 0.25 * _clamp01(level_now / 0.8)
        ),
        "Crecimiento": (
            0.40 * rising_score
            + 0.35 * _clamp01(level_now / 0.8)
            + 0.25 * _clamp01(active_share / 0.5)
        ),
        "Masiva": (
            0.45 * _clamp01(level_now / 0.85)
            + 0.30 * high_share
            + 0.25 * flat_score
        ),
        "Saturada": (
            0.35 * _clamp01(level_now / 0.7)
            + 0.40 * _clamp01(persistence / 0.7)
            + 0.25 * flat_score
        ),
        "En declive": (
            0.50 * (1 - _clamp01(level_now / 0.5))
            + 0.30 * falling_score
            + 0.20 * _clamp01(peak_age / 14)
        ),
    }

    # Deterministic ladder: short-term velocity first, long-term base as context.
    if weak_signal:
        stage = "Naciente"
    elif peaked_before and level_now <= DECLINE_LEVEL:
        stage = "En declive"
    elif rising:
        stage = "Emergente" if active_share < NICHE_SHARE else "Crecimiento"
    elif level_now >= MATURE_LEVEL:
        stage = "Saturada" if persistence >= PLATEAU_SHARE else "Masiva"
    elif peaked_before:
        stage = "En declive"
    else:
        stage = "Naciente"

    scores[stage] = max(scores[stage], 0.7)
    runner_up = max(value for key, value in scores.items() if key != stage)
    margin = max(scores[stage] - runner_up, 0.0)
    confidence = min(0.95, 0.55 + 0.25 * scores[stage] + 0.3 * margin)

    avg_recent = levels["week"] * 100
    avg_early = levels["year"] * 100

    metrics = {
        "avg_interest": round(weighted_level * 100, 1),
        "avg_recent": round(avg_recent, 1),
        "avg_early": round(avg_early, 1),
        "max_interest": 100.0 if raw_peak > 0 else 0.0,
        "growth_ratio": round((avg_recent + 1) / (avg_early + 1), 2),
        "slope_recent": round(velocity_week * 100, 3),
        "peak_position": round(peak_idx / max(n - 1, 1), 2),
        "volatility": round(float(np.std(normalized) * 100), 2),
        "current_to_peak": round(level_now, 3),
        "peak_age_points": peak_age,
        "acceleration_now": round(accel_now, 3),
        "acceleration_week": round(accel_week, 3),
        "baseline_momentum": round(baseline_momentum, 3),
        "momentum_7": round(velocity_week, 3),
        "momentum_30": round(velocity_month, 3),
        "persistence": round(persistence, 3),
        "days_analyzed": n,
    }

    return LifecycleResult(
        stage=stage,
        confidence=round(confidence, 2),
        description=STAGE_DESCRIPTIONS[stage],
        metrics=metrics,
        stage_scores={k: round(v, 3) for k, v in scores.items()},
    )
