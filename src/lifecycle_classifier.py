"""Classify a trend's lifecycle stage from Google Trends time series."""

from dataclasses import dataclass

import numpy as np
import pandas as pd

from src.keyword_generator import LIFECYCLE_STAGES

STAGE_DESCRIPTIONS = {
    "Naciente": (
        "La señal acaba de aparecer y todavía no formó un pico histórico relevante. "
        "Conviene observar si gana persistencia."
    ),
    "Emergente": (
        "El interés acelera recientemente desde una presencia histórica limitada. "
        "Es una ventana temprana para explorar y posicionarse."
    ),
    "Crecimiento": (
        "La curva mantiene una subida sostenida y se acerca a su máximo observado. "
        "La adopción continúa expandiéndose."
    ),
    "Masiva": (
        "El interés actual permanece cerca del máximo y concentra una exposición amplia. "
        "La diferenciación resulta más difícil."
    ),
    "Saturada": (
        "El interés continúa alto y persistente, pero la curva se estabilizó. "
        "El riesgo de repetición aumenta."
    ),
    "En declive": (
        "El pico quedó atrás y el interés reciente cayó de forma significativa. "
        "Conviene evitar activaciones genéricas o buscar una nueva derivación."
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


def classify_lifecycle(data: pd.DataFrame) -> LifecycleResult:
    """
    Classify one global lifecycle stage from the complete observed curve.

    Google Trends values are relative, so the decision uses curve geometry:
    current level vs. peak, peak age, persistence and 7/30-point momentum.
    """
    series = _aggregate_series(data).dropna()
    values = np.clip(series.values.astype(float), 0, None)
    n = len(values)

    if n < 7:
        raise ValueError("Se necesitan al menos 7 días de datos para clasificar.")

    # A centered 3-point mean limits one-point noise without erasing a short fad.
    smooth_window = 3 if n >= 14 else 1
    smoothed = (
        pd.Series(values)
        .rolling(smooth_window, center=True, min_periods=1)
        .mean()
        .values
    )
    raw_peak = float(np.max(smoothed))

    if raw_peak <= 0:
        normalized = np.zeros(n)
    else:
        normalized = smoothed / raw_peak

    peak_idx = int(np.argmax(normalized))
    peak_age = n - 1 - peak_idx
    peak_position = peak_idx / (n - 1)
    recent_7 = normalized[-min(7, n) :]
    recent_30 = normalized[-min(30, n) :]
    previous_30 = normalized[-min(60, n) : -min(30, n)]
    if len(previous_30) == 0:
        split = max(1, n // 2)
        previous_30 = normalized[:split]

    current_to_peak = float(np.mean(recent_7))
    avg_recent = float(np.mean(recent_30) * 100)
    avg_early = float(np.mean(previous_30) * 100)
    avg_all = float(np.mean(normalized) * 100)
    growth_ratio = (avg_recent + 1) / (avg_early + 1)
    momentum_7 = _linear_slope(recent_7) * max(len(recent_7) - 1, 1)
    momentum_30 = _linear_slope(recent_30) * max(len(recent_30) - 1, 1)
    slope_recent = _linear_slope(recent_30) * 100
    persistence = float(np.mean(normalized >= 0.5))
    active_share = float(np.mean(normalized >= 0.1))
    recent_high_share = float(np.mean(recent_30 >= 0.7))
    peak_age_score = _clamp01(peak_age / max(min(60, n // 2), 1))
    peak_recency = 1 - peak_age_score
    positive_7 = _clamp01(momentum_7 / 0.35)
    positive_30 = _clamp01(momentum_30 / 0.6)
    negative_7 = _clamp01(-momentum_7 / 0.35)
    negative_30 = _clamp01(-momentum_30 / 0.6)
    flattening = 1 - _clamp01(abs(momentum_30) / 0.2)
    low_raw_signal = raw_peak < 5
    meaningful_past_peak = raw_peak >= 5 and peak_age >= 3

    scores: dict[str, float] = {
        "Naciente": (
            0.45 * (1 - _clamp01(active_share / 0.12))
            + 0.30 * peak_recency
            + 0.25 * (1 - _clamp01(current_to_peak / 0.5))
        ),
        "Emergente": (
            0.35 * peak_recency
            + 0.35 * max(positive_7, positive_30)
            + 0.30 * (1 - _clamp01(persistence / 0.25))
        ),
        "Crecimiento": (
            0.40 * current_to_peak
            + 0.40 * positive_30
            + 0.20 * _clamp01(active_share / 0.35)
        ),
        "Masiva": (
            0.50 * current_to_peak
            + 0.30 * recent_high_share
            + 0.20 * flattening
        ),
        "Saturada": (
            0.35 * current_to_peak
            + 0.35 * _clamp01(persistence / 0.4)
            + 0.30 * flattening
        ),
        "En declive": (
            0.45 * (1 - current_to_peak)
            + 0.25 * peak_age_score
            + 0.20 * negative_30
            + 0.10 * negative_7
        ),
    }

    # Eligibility guards encode the ordered lifecycle semantics.
    if peak_age > 14 or max(momentum_7, momentum_30) <= 0:
        scores["Emergente"] = 0.0
    if momentum_30 <= 0.03 or active_share < 0.08:
        scores["Crecimiento"] = 0.0
    if (
        current_to_peak < 0.65
        or recent_high_share < 0.35
        or momentum_30 > 0.08
    ):
        scores["Masiva"] = 0.0
    if current_to_peak < 0.45 or persistence < 0.18 or momentum_30 > 0.05:
        scores["Saturada"] = 0.0
    if not meaningful_past_peak or current_to_peak > 0.7:
        scores["En declive"] = 0.0

    # Hard invariants prevent logically impossible labels.
    if meaningful_past_peak and current_to_peak <= 0.35:
        stage = "En declive"
        scores[stage] = max(scores[stage], 0.9)
    elif low_raw_signal or (active_share < 0.04 and peak_age <= 7):
        stage = "Naciente"
        scores[stage] = max(scores[stage], 0.82)
    else:
        stage = max(scores, key=scores.get)

    top_score = scores[stage]
    sorted_scores = sorted(scores.values(), reverse=True)
    margin = sorted_scores[0] - sorted_scores[1] if len(sorted_scores) > 1 else 0.5
    confidence = min(0.95, 0.45 + top_score * 0.3 + margin * 0.4)

    metrics = {
        "avg_interest": round(avg_all, 1),
        "avg_recent": round(avg_recent, 1),
        "avg_early": round(avg_early, 1),
        "max_interest": 100.0 if raw_peak > 0 else 0.0,
        "growth_ratio": round(growth_ratio, 2),
        "slope_recent": round(slope_recent, 3),
        "peak_position": round(peak_position, 2),
        "volatility": round(float(np.std(normalized) * 100), 2),
        "current_to_peak": round(current_to_peak, 3),
        "peak_age_points": peak_age,
        "momentum_7": round(momentum_7, 3),
        "momentum_30": round(momentum_30, 3),
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
