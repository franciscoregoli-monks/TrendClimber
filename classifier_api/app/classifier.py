"""Clasifica tipo de curva (fad / mode / classic) y estadio del ciclo de vida."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Literal

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

InternalCurve = Literal["fad", "fashion", "basic"]
TipoTrend = Literal["fad", "mode", "classic"]
ModelName = Literal["bass", "lognormal", "logistic_decay", "weibull"]

LIFECYCLE_STAGES = [
    "Naciente",
    "Emergente",
    "Crecimiento",
    "Masiva",
    "Saturada",
    "En declive",
]

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

TIPO_DESCRIPTIONS: dict[TipoTrend, str] = {
    "fad": "Pico corto: sube rápido y se desvanece (moda pasajera).",
    "mode": "Campana clásica de moda: crece, pico y cae en madurez.",
    "classic": "Producto clásico: subida lenta, meseta larga y declive gradual.",
}

CURVE_TO_TIPO: dict[InternalCurve, TipoTrend] = {
    "fad": "fad",
    "fashion": "mode",
    "basic": "classic",
}

DISTINCTIVE_CURVE_MODELS: dict[InternalCurve, ModelName] = {
    "fad": "weibull",
    "fashion": "lognormal",
    "basic": "logistic_decay",
}


@dataclass
class LifecycleResult:
    stage: str
    confidence: float
    description: str
    metrics: dict
    stage_scores: dict[str, float]


def _aggregate_series(data: pd.DataFrame) -> pd.Series:
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
    peak_idx = int(np.argmax(values))
    peak_position = peak_idx / (n - 1)

    slope_recent = _linear_slope(recent)

    growth_ratio = (avg_recent + 1) / (avg_early + 1)
    volatility = float(np.std(values)) if n > 1 else 0.0

    scores: dict[str, float] = {}
    scores["Naciente"] = (
        0.5 * (1 - min(avg_all / 20, 1))
        + 0.3 * (1 - min(growth_ratio / 1.5, 1))
        + 0.2 * (1 - min(max_val / 25, 1))
    )

    emergente_growth = min(max(growth_ratio - 1, 0) / 2, 1)
    scores["Emergente"] = (
        0.4 * (1 - min(avg_recent / 35, 1))
        + 0.4 * emergente_growth
        + 0.2 * min(max(slope_recent, 0) / 2, 1)
    )

    scores["Crecimiento"] = (
        0.3 * min(avg_recent / 50, 1)
        + 0.4 * min(max(slope_recent, 0) / 3, 1)
        + 0.3 * (1 - peak_position if peak_position > 0.3 else 0.5)
    )

    scores["Masiva"] = (
        0.5 * min(avg_recent / 70, 1)
        + 0.3 * min(max_val / 80, 1)
        + 0.2 * (1 - abs(peak_position - 0.7))
    )

    was_high = min(max(np.mean(mid), avg_early) / 60, 1)
    flattening = 1 - min(abs(slope_recent) / 2, 1) if avg_recent > 40 else 0
    slight_decline = min(max(-slope_recent, 0) / 3, 1) if avg_recent > 35 else 0
    scores["Saturada"] = 0.4 * was_high + 0.35 * flattening + 0.25 * slight_decline

    past_peak = 1.0 if peak_position < 0.6 else max(0, 1 - peak_position)
    declining = min(max(-slope_recent, 0) / 4, 1)
    drop_from_peak = min((max_val - avg_recent) / max(max_val, 1), 1)
    scores["En declive"] = 0.35 * past_peak + 0.35 * declining + 0.3 * drop_from_peak

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


def classify_product_curve_type(stage: str, metrics: dict[str, Any]) -> InternalCurve:
    metrics = metrics or {}
    peak = float(metrics.get("peak_position", 0.5))
    vol = float(metrics.get("volatility", 0))
    growth = float(metrics.get("growth_ratio", 1))
    avg_early = float(metrics.get("avg_early", 0))
    avg_recent = float(metrics.get("avg_recent", 0))

    if growth >= 8 or (avg_early <= 5 and avg_recent >= 20):
        return "fad"
    if vol >= 25 and growth >= 4:
        return "fad"
    if peak >= 0.65 and growth >= 5 and avg_early <= 10:
        return "fad"
    if stage in ("Naciente", "Emergente") and peak < 0.4 and vol > 15:
        return "fad"

    if growth >= 4 or vol >= 28:
        return "fashion"
    if avg_early <= 8 and avg_recent >= 25:
        return "fashion"
    if (
        growth < 1.8
        and vol < 18
        and 0.25 < peak < 0.72
        and stage in ("Saturada", "En declive")
    ):
        return "basic"
    if growth < 1.3 and vol < 12 and peak < 0.55:
        return "basic"

    return "fashion"


def _fad_signals(y: np.ndarray, metrics: dict[str, Any]) -> float:
    n = len(y)
    if n < 3:
        return 0.0

    peak_idx = int(np.argmax(y))
    peak_pos = peak_idx / max(n - 1, 1)
    y_norm = y / max(float(np.max(y)), 1e-6)
    half_width = float(np.sum(y_norm > 0.5)) / n

    growth = float(metrics.get("growth_ratio", 1))
    vol = float(metrics.get("volatility", 0))
    avg_early = float(metrics.get("avg_early", 0))
    avg_recent = float(metrics.get("avg_recent", 0))

    score = 0.0
    if avg_early <= 5 and avg_recent >= 20:
        score += 0.35
    elif avg_early <= 10 and avg_recent >= 35:
        score += 0.22

    if growth >= 15:
        score += 0.3
    elif growth >= 8:
        score += 0.22
    elif growth >= 4:
        score += 0.12

    if vol >= 30:
        score += 0.15
    elif vol >= 18:
        score += 0.08

    if half_width <= 0.25:
        score += 0.2
    elif half_width <= 0.38:
        score += 0.1

    if peak_pos <= 0.35:
        score += 0.22
    elif peak_pos >= 0.65 and growth >= 5 and avg_early <= 12:
        score += 0.25

    tail = y_norm[-max(5, n // 4) :]
    tail_share = float(np.sum(tail)) / max(float(np.sum(y_norm)), 1e-6)
    if tail_share >= 0.55 and growth >= 3:
        score += 0.12

    return min(score, 1.0)


def _basic_signals(y: np.ndarray, metrics: dict[str, Any]) -> float:
    n = len(y)
    peak_idx = int(np.argmax(y))
    peak_pos = peak_idx / max(n - 1, 1)
    y_norm = y / max(float(np.max(y)), 1e-6)
    plateau = float(np.mean(y_norm > 0.75))
    half_width = float(np.sum(y_norm > 0.5)) / n

    growth = float(metrics.get("growth_ratio", 1))
    vol = float(metrics.get("volatility", 0))
    avg_early = float(metrics.get("avg_early", 0))
    avg_recent = float(metrics.get("avg_recent", 0))

    if growth >= 4 or vol >= 28:
        return 0.0
    if avg_early <= 8 and avg_recent >= 25:
        return 0.0
    if growth >= 8:
        return 0.0

    score = 0.0
    if plateau >= 0.35:
        score += 0.35
    elif plateau >= 0.22:
        score += 0.15

    if half_width >= 0.45:
        score += 0.25
    elif half_width >= 0.35:
        score += 0.1

    if 0.3 <= peak_pos <= 0.68:
        score += 0.2

    if growth < 2:
        score += 0.15
    if vol < 18:
        score += 0.1

    return min(score, 1.0)


def _shape_scores(y: np.ndarray, metrics: dict[str, Any] | None = None) -> dict[InternalCurve, float]:
    metrics = metrics or {}
    n = len(y)
    peak_idx = int(np.argmax(y))
    peak_pos = peak_idx / max(n - 1, 1)
    y_norm = y / max(float(np.max(y)), 1e-6)

    half_width = float(np.sum(y_norm > 0.5)) / n
    plateau = float(np.mean(y_norm > 0.75))
    rise = (y_norm[peak_idx] - y_norm[0]) / max(peak_idx, 1)
    decay = (y_norm[peak_idx] - y_norm[-1]) / max(n - peak_idx - 1, 1)

    fad = (1 - min(peak_pos / 0.4, 1)) * 0.55 + (1 - min(half_width / 0.3, 1)) * 0.45
    basic = min(plateau * 1.2, 1) * 0.45 + min(max(peak_pos - 0.5, 0) / 0.5, 1) * 0.55
    if decay < rise * 0.4 and plateau > 0.25:
        basic = min(basic + 0.15, 1.0)

    mid_peak = max(0.0, 1 - abs(peak_pos - 0.45) / 0.45)
    fashion = (
        mid_peak * 0.55
        + min(half_width / 0.45, 1) * 0.25
        + min(rise, decay) / max(max(rise, decay), 1e-6) * 0.2
    )

    scores: dict[InternalCurve, float] = {"fad": fad, "fashion": fashion, "basic": basic}
    fad_strength = _fad_signals(y, metrics)
    basic_strength = _basic_signals(y, metrics)

    scores["fad"] = min(1.0, scores["fad"] * 0.45 + fad_strength * 0.55)
    if fad_strength >= 0.4:
        scores["basic"] *= max(0.15, 1 - fad_strength)
    if basic_strength < 0.35:
        scores["basic"] *= 0.45
    scores["basic"] = min(1.0, scores["basic"] * 0.5 + basic_strength * 0.5)

    return scores


def bass_rate(t: np.ndarray, m: float, p: float, q: float) -> np.ndarray:
    t = np.asarray(t, dtype=float)
    p = max(p, 1e-6)
    z = np.exp(-(p + q) * (t - 1))
    return m * (p + q) ** 2 / p * z / (1 + (q / p) * z) ** 2


def lognormal_rate(t: np.ndarray, a: float, mu: float, sigma: float) -> np.ndarray:
    t = np.maximum(np.asarray(t, dtype=float), 0.5)
    sigma = max(sigma, 0.05)
    return (
        a
        / (t * sigma * np.sqrt(2 * np.pi))
        * np.exp(-((np.log(t) - mu) ** 2) / (2 * sigma**2))
    )


def logistic_decay_rate(t: np.ndarray, L: float, k: float, t0: float, delta: float) -> np.ndarray:
    t = np.asarray(t, dtype=float)
    adoption = L / (1 + np.exp(-k * (t - t0)))
    return adoption * np.exp(-delta * (t - 1) / max(t[-1], 1))


def weibull_rate(t: np.ndarray, a: float, k: float, lam: float) -> np.ndarray:
    t = np.maximum(np.asarray(t, dtype=float), 0.1)
    lam = max(lam, 0.5)
    k = max(k, 0.5)
    return a * (k / lam) * (t / lam) ** (k - 1) * np.exp(-((t / lam) ** k))


def _t_axis(n: int) -> np.ndarray:
    return np.arange(1, n + 1, dtype=float)


def _initial_guess(model: ModelName, y: np.ndarray, curve_type: InternalCurve) -> tuple[float, ...]:
    peak = float(np.max(y))
    n = len(y)
    if model == "bass":
        if curve_type == "fad":
            return peak * 1.2, 0.08, 0.45
        if curve_type == "basic":
            return peak * 1.5, 0.008, 0.12
        return peak * 1.3, 0.02, 0.25
    if model == "lognormal":
        mu = np.log(max(np.argmax(y) + 1, 2))
        return peak, mu, 0.45
    if model == "logistic_decay":
        delta = 0.002 if curve_type == "basic" else 0.015
        return peak * 1.1, 0.15, n * 0.45, delta
    k = 3.5 if curve_type == "fad" else 2.0
    return peak, k, max(n * 0.25, 2.0)


def _bounds(model: ModelName, peak: float, n: int) -> tuple[tuple, tuple]:
    hi = max(peak * 3, 100)
    if model == "bass":
        return (0, 1e-5, 1e-5), (hi * 2, 0.5, 1.0)
    if model == "lognormal":
        return (0, -2, 0.05), (hi * 2, np.log(n + 2), 2.0)
    if model == "logistic_decay":
        return (0, 0.01, 1, 0), (hi * 2, 2.0, n * 1.5, 0.2)
    return (0, 0.5, 0.5), (hi * 2, 10.0, n * 2)


def _fit_model(
    model: ModelName,
    y: np.ndarray,
    curve_type: InternalCurve,
) -> tuple[tuple[float, ...], float] | None:
    try:
        from scipy.optimize import curve_fit

        t = _t_axis(len(y))
        p0 = _initial_guess(model, y, curve_type)
        bounds = _bounds(model, float(np.max(y)), len(y))
        funcs = {
            "bass": bass_rate,
            "lognormal": lognormal_rate,
            "logistic_decay": logistic_decay_rate,
            "weibull": weibull_rate,
        }
        params, _ = curve_fit(
            funcs[model],
            t,
            y,
            p0=p0,
            bounds=bounds,
            maxfev=8000,
        )
        pred = funcs[model](t, *tuple(params))
        rmse = float(np.sqrt(np.mean((pred - y) ** 2)))
        return tuple(float(x) for x in params), rmse
    except Exception as exc:
        logger.debug("Fit failed for %s: %s", model, exc)
        return None


def classify_product_curve_from_series(
    series: pd.Series | np.ndarray,
    *,
    stage: str = "",
    metrics: dict[str, Any] | None = None,
) -> dict[str, Any]:
    values = pd.Series(series).dropna().astype(float).values
    y = np.clip(values, 0, None)

    if len(y) < 7:
        curve_type = classify_product_curve_type(stage, metrics or {})
        return {"curveType": curve_type, "source": "heuristic"}

    metrics = metrics or {}
    fad_strength = _fad_signals(y, metrics)

    if fad_strength >= 0.55:
        return {"curveType": "fad", "source": "heuristic"}

    shape = _shape_scores(y, metrics)
    fit_errors: dict[InternalCurve, float] = {}

    for curve_type, model_name in DISTINCTIVE_CURVE_MODELS.items():
        fitted = _fit_model(model_name, y, curve_type)
        if not fitted:
            continue
        _, rmse = fitted
        fit_errors[curve_type] = rmse

    if not fit_errors:
        curve_type = classify_product_curve_type(stage, metrics or {})
        return {"curveType": curve_type, "source": "heuristic"}

    ranked_shape = sorted(shape.items(), key=lambda item: item[1], reverse=True)
    best_shape_type, best_shape_score = ranked_shape[0]
    second_shape_score = ranked_shape[1][1]
    basic_strength = _basic_signals(y, metrics)

    if best_shape_score - second_shape_score >= 0.2:
        best_type = best_shape_type
    else:
        min_rmse = min(fit_errors.values())
        max_rmse = max(fit_errors.values())
        combined: dict[InternalCurve, float] = {}
        for curve_type in ("fad", "fashion", "basic"):
            if curve_type in fit_errors:
                if max_rmse == min_rmse:
                    fit_score = 1.0
                else:
                    fit_score = 1 - (fit_errors[curve_type] - min_rmse) / (max_rmse - min_rmse)
            else:
                fit_score = 0.0
            combined[curve_type] = 0.55 * shape[curve_type] + 0.45 * fit_score
        best_type = max(combined, key=combined.get)

    if best_type == "basic" and (fad_strength >= 0.42 or basic_strength < 0.4):
        best_type = "fad" if fad_strength >= 0.35 else "fashion"
    elif best_type != "fad" and fad_strength >= 0.58:
        best_type = "fad"

    return {"curveType": best_type, "source": "curve_fit"}


def to_tipo(curve_type: str) -> TipoTrend:
    return CURVE_TO_TIPO.get(curve_type, "mode")
