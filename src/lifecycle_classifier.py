"""Classify a trend's lifecycle stage from Google Trends time series."""

from dataclasses import dataclass

import numpy as np
import pandas as pd

from src.keyword_generator import LIFECYCLE_STAGES

STAGE_DESCRIPTIONS = {
    "Naciente": (
        "La conversación apenas comienza. Volumen de búsqueda muy bajo; "
        "detectarla ahora ofrece ventaja de first-mover."
    ),
    "Emergente": (
        "La tendencia despierta interés creciente desde una base baja. "
        "Momento ideal para explorar y posicionarse con autenticidad."
    ),
    "Crecimiento": (
        "Adopción acelerada y visibilidad en aumento. "
        "Buen momento para activar campañas antes de la saturación."
    ),
    "Masiva": (
        "Alcanzó pico de relevancia y alta visibilidad mainstream. "
        "Participar aún tiene impacto, pero la diferenciación es más difícil."
    ),
    "Saturada": (
        "Alta exposición pero estancamiento o repetición. "
        "El riesgo de parecer forzado aumenta; conviene un ángulo único."
    ),
    "En declive": (
        "Pierde tracción y el interés cae. "
        "Evitar activaciones genéricas; buscar sub-tendencias o pivotar."
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


def classify_lifecycle(data: pd.DataFrame) -> LifecycleResult:
    """
    Classify trend lifecycle from interest-over-time DataFrame.

    Uses combined keyword signal and analyzes:
    - absolute level, recent vs early growth, peak position, momentum
    """
    series = _aggregate_series(data).dropna()
    values = series.values.astype(float)
    n = len(values)

    if n < 7:
        raise ValueError("Se necesitan al menos 7 días de datos para clasificar.")

    recent_window = max(7, n // 4)
    early_window = max(7, n // 4)

    recent = values[-recent_window:]
    early = values[:early_window]
    mid = values[n // 3 : 2 * n // 3] if n >= 15 else values

    avg_all = float(np.mean(values))
    avg_recent = float(np.mean(recent))
    avg_early = float(np.mean(early))
    max_val = float(np.max(values))
    min_val = float(np.min(values))
    peak_idx = int(np.argmax(values))
    peak_position = peak_idx / (n - 1)  # 0=start, 1=end

    slope_all = _linear_slope(values)
    slope_recent = _linear_slope(recent)
    slope_early = _linear_slope(early)

    growth_ratio = (avg_recent + 1) / (avg_early + 1)
    momentum = avg_recent - avg_early
    volatility = float(np.std(values)) if n > 1 else 0.0

    # Normalized feature scores per stage (0-1)
    scores: dict[str, float] = {}

    # Naciente: very low volume, minimal growth
    scores["Naciente"] = (
        0.5 * (1 - min(avg_all / 20, 1))
        + 0.3 * (1 - min(growth_ratio / 1.5, 1))
        + 0.2 * (1 - min(max_val / 25, 1))
    )

    # Emergente: low base + strong recent growth
    emergente_growth = min(max(growth_ratio - 1, 0) / 2, 1)
    scores["Emergente"] = (
        0.4 * (1 - min(avg_recent / 35, 1))
        + 0.4 * emergente_growth
        + 0.2 * min(max(slope_recent, 0) / 2, 1)
    )

    # Crecimiento: moderate-high volume, positive momentum, peak not yet at end
    scores["Crecimiento"] = (
        0.3 * min(avg_recent / 50, 1)
        + 0.4 * min(max(slope_recent, 0) / 3, 1)
        + 0.3 * (1 - peak_position if peak_position > 0.3 else 0.5)
    )

    # Masiva: high volume near peak
    scores["Masiva"] = (
        0.5 * min(avg_recent / 70, 1)
        + 0.3 * min(max_val / 80, 1)
        + 0.2 * (1 - abs(peak_position - 0.7))
    )

    # Saturada: was high, now flat or slightly declining at high level
    was_high = min(max(np.mean(mid), avg_early) / 60, 1)
    flattening = 1 - min(abs(slope_recent) / 2, 1) if avg_recent > 40 else 0
    slight_decline = min(max(-slope_recent, 0) / 3, 1) if avg_recent > 35 else 0
    scores["Saturada"] = 0.4 * was_high + 0.35 * flattening + 0.25 * slight_decline

    # En declive: clear negative trend, peak in the past
    past_peak = 1.0 if peak_position < 0.6 else max(0, 1 - peak_position)
    declining = min(max(-slope_recent, 0) / 4, 1)
    drop_from_peak = min((max_val - avg_recent) / max(max_val, 1), 1)
    scores["En declive"] = 0.35 * past_peak + 0.35 * declining + 0.3 * drop_from_peak

    # Pick best stage
    stage = max(scores, key=scores.get)
    top_score = scores[stage]
    sorted_scores = sorted(scores.values(), reverse=True)
    margin = sorted_scores[0] - sorted_scores[1] if len(sorted_scores) > 1 else 0.5
    confidence = min(0.95, 0.45 + top_score * 0.3 + margin * 0.4)

    metrics = {
        "avg_interest": round(avg_all, 1),
        "avg_recent": round(avg_recent, 1),
        "avg_early": round(avg_early, 1),
        "max_interest": round(max_val, 1),
        "growth_ratio": round(growth_ratio, 2),
        "slope_recent": round(slope_recent, 3),
        "peak_position": round(peak_position, 2),
        "volatility": round(volatility, 2),
        "days_analyzed": n,
    }

    return LifecycleResult(
        stage=stage,
        confidence=round(confidence, 2),
        description=STAGE_DESCRIPTIONS[stage],
        metrics=metrics,
        stage_scores={k: round(v, 3) for k, v in scores.items()},
    )
