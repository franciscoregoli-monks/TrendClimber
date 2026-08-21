"""Product lifecycle curve models — Bass, Log-Normal, Modified Logistic, Weibull."""

from __future__ import annotations

import logging
from typing import Any, Literal

import numpy as np
import pandas as pd

from src.trends_fetcher import PROPHET_FORECAST_DAYS, _forecast_start_day, build_pytrends_forecast

logger = logging.getLogger(__name__)

ProductCurveType = Literal["fad", "fashion", "basic"]
ModelName = Literal["bass", "lognormal", "logistic_decay", "weibull"]

MODEL_LABELS: dict[ModelName, str] = {
    "bass": "Bass Diffusion",
    "lognormal": "Log-Normal",
    "logistic_decay": "Logística modificada",
    "weibull": "Weibull (Fad)",
}

CURVE_TYPE_MODELS: dict[ProductCurveType, list[ModelName]] = {
    "fad": ["weibull", "bass"],
    "fashion": ["lognormal", "bass"],
    "basic": ["logistic_decay", "bass"],
}

# Primary model per curve type — used to classify from Google Trends shape.
DISTINCTIVE_CURVE_MODELS: dict[ProductCurveType, ModelName] = {
    "fad": "weibull",
    "fashion": "lognormal",
    "basic": "logistic_decay",
}


def classify_product_curve_type(stage: str, metrics: dict[str, Any]) -> ProductCurveType:
    """Heuristic fallback when the trends series is too short to fit curves."""
    metrics = metrics or {}
    peak = float(metrics.get("peak_position", 0.5))
    vol = float(metrics.get("volatility", 0))
    growth = float(metrics.get("growth_ratio", 1))
    avg_early = float(metrics.get("avg_early", 0))
    avg_recent = float(metrics.get("avg_recent", 0))

    # Viral fad: explosive growth from a low baseline (incl. late peaks still climbing).
    if growth >= 8 or (avg_early <= 5 and avg_recent >= 20):
        return "fad"
    if vol >= 25 and growth >= 4:
        return "fad"
    if peak >= 0.65 and growth >= 5 and avg_early <= 10:
        return "fad"
    if stage in ("Naciente", "Emergente") and peak < 0.4 and vol > 15:
        return "fad"

    # Basic: slow build, sustained plateau, moderate volatility — not a viral spike.
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
    """Strong fad indicators (0–1). Late viral peaks score high here."""
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
    """Basic product needs plateau + moderate growth — viral spikes disqualify."""
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


def _shape_scores(y: np.ndarray, metrics: dict[str, Any] | None = None) -> dict[ProductCurveType, float]:
    """Score curve types from Google Trends shape features."""
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
    fashion = mid_peak * 0.55 + min(half_width / 0.45, 1) * 0.25 + min(rise, decay) / max(max(rise, decay), 1e-6) * 0.2

    scores: dict[ProductCurveType, float] = {"fad": fad, "fashion": fashion, "basic": basic}

    fad_strength = _fad_signals(y, metrics)
    basic_strength = _basic_signals(y, metrics)

    scores["fad"] = min(1.0, scores["fad"] * 0.45 + fad_strength * 0.55)
    if fad_strength >= 0.4:
        scores["basic"] *= max(0.15, 1 - fad_strength)
    if basic_strength < 0.35:
        scores["basic"] *= 0.45
    scores["basic"] = min(1.0, scores["basic"] * 0.5 + basic_strength * 0.5)

    return scores


def classify_product_curve_from_series(
    series: pd.Series | np.ndarray,
    *,
    stage: str = "",
    metrics: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Classify fad / fashion / basic from the Google Trends interest-over-time curve.

    Combines shape features (peak position, width, plateau) with PLC model fit
    (Weibull / Log-Normal / Modified Logistic) and picks the best combined score.
    """
    values = pd.Series(series).dropna().astype(float).values
    y = np.clip(values, 0, None)

    if len(y) < 7:
        curve_type = classify_product_curve_type(stage, metrics or {})
        return {
            "curveType": curve_type,
            "modelName": CURVE_TYPE_MODELS[curve_type][0],
            "fitError": None,
            "source": "heuristic",
        }

    metrics = metrics or {}
    fad_strength = _fad_signals(y, metrics)

    if fad_strength >= 0.55:
        return {
            "curveType": "fad",
            "modelName": "weibull",
            "fitError": None,
            "source": "heuristic",
        }

    shape = _shape_scores(y, metrics)
    fit_errors: dict[ProductCurveType, float] = {}
    fit_models: dict[ProductCurveType, ModelName] = {}

    for curve_type, model_name in DISTINCTIVE_CURVE_MODELS.items():
        fitted = _fit_model(model_name, y, curve_type)
        if not fitted:
            continue
        _, rmse = fitted
        fit_errors[curve_type] = rmse
        fit_models[curve_type] = model_name

    if not fit_errors:
        curve_type = classify_product_curve_type(stage, metrics or {})
        return {
            "curveType": curve_type,
            "modelName": CURVE_TYPE_MODELS[curve_type][0],
            "fitError": None,
            "source": "heuristic",
        }

    ranked_shape = sorted(shape.items(), key=lambda item: item[1], reverse=True)
    best_shape_type, best_shape_score = ranked_shape[0]
    second_shape_score = ranked_shape[1][1]

    basic_strength = _basic_signals(y, metrics)

    if best_shape_score - second_shape_score >= 0.2:
        best_type = best_shape_type
    else:
        min_rmse = min(fit_errors.values())
        max_rmse = max(fit_errors.values())
        combined: dict[ProductCurveType, float] = {}
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

    return {
        "curveType": best_type,
        "modelName": fit_models.get(best_type, DISTINCTIVE_CURVE_MODELS[best_type]),
        "fitError": round(fit_errors[best_type], 2) if best_type in fit_errors else None,
        "source": "curve_fit",
    }


def _t_axis(n: int) -> np.ndarray:
    return np.arange(1, n + 1, dtype=float)


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


def _predict(model: ModelName, t: np.ndarray, params: tuple[float, ...]) -> np.ndarray:
    if model == "bass":
        return bass_rate(t, *params)
    if model == "lognormal":
        return lognormal_rate(t, *params)
    if model == "logistic_decay":
        return logistic_decay_rate(t, *params)
    return weibull_rate(t, *params)


def _initial_guess(model: ModelName, y: np.ndarray, curve_type: ProductCurveType) -> tuple[float, ...]:
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
    curve_type: ProductCurveType,
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
        pred = _predict(model, t, tuple(params))
        rmse = float(np.sqrt(np.mean((pred - y) ** 2)))
        return tuple(float(x) for x in params), rmse
    except Exception as exc:
        logger.debug("Fit failed for %s: %s", model, exc)
        return None


def _best_model(
    y: np.ndarray,
    curve_type: ProductCurveType,
) -> tuple[ModelName, tuple[float, ...], float] | None:
    best: tuple[ModelName, tuple[float, ...], float] | None = None
    for name in CURVE_TYPE_MODELS[curve_type]:
        fitted = _fit_model(name, y, curve_type)
        if not fitted:
            continue
        params, rmse = fitted
        if best is None or rmse < best[2]:
            best = (name, params, rmse)
    return best


def build_lifecycle_forecast(
    series: pd.Series,
    periods: int = PROPHET_FORECAST_DAYS,
    *,
    stage: str,
    metrics: dict[str, Any],
    related_queries: dict[str, Any] | None = None,
    geo: str = "ES",
) -> dict | None:
    """Fit lifecycle curve model and project forward."""
    series = series.sort_index().astype(float)
    if len(series) < 7:
        return None

    y = series.values.astype(float)
    y = np.clip(y, 0, None)
    classified = classify_product_curve_from_series(
        y,
        stage=stage,
        metrics=metrics,
    )
    curve_type = classified["curveType"]
    fit = _best_model(y, curve_type)
    if not fit:
        return None

    model_name, params, rmse = fit
    n = len(y)
    t_hist = _t_axis(n)
    fitted_hist = _predict(model_name, t_hist, params)
    last_actual = float(y[-1])
    scale = last_actual / fitted_hist[-1] if fitted_hist[-1] > 1e-6 else 1.0

    first_day = _forecast_start_day(series)
    t_future = np.arange(n + 1, n + periods + 1, dtype=float)
    future_vals = np.clip(_predict(model_name, t_future, params) * scale, 0, 100)

    resid = y - fitted_hist * scale
    std = float(np.std(resid[-min(14, n) :])) if n > 2 else max(last_actual * 0.1, 1.0)
    std = max(std, 1.0)

    timeline: list[dict] = []
    for i, ds_offset in enumerate(range(periods)):
        ds = first_day + pd.Timedelta(days=ds_offset)
        pred = float(future_vals[i])
        timeline.append(
            {
                "date": ds.strftime("%Y-%m-%d"),
                "actual": None,
                "forecast": round(pred, 2),
                "lower": round(max(pred - 1.28 * std, 0), 2),
                "upper": round(min(pred + 1.28 * std, 100), 2),
                "isFuture": True,
            }
        )

    return {
        "method": "lifecycle_curve",
        "hasSeasonality": False,
        "forecastDays": periods,
        "forecastFrom": first_day.strftime("%Y-%m-%d"),
        "timeline": timeline,
        "seasonality": [],
        "label": (
            f"{MODEL_LABELS[model_name]} · curva {curve_type} "
            f"(Product Life Cycle, RMSE={rmse:.1f})"
        ),
        "curveType": curve_type,
        "modelName": model_name,
        "fitError": round(rmse, 2),
        "risingQuery": None,
    }


def build_forecast(
    series: pd.Series,
    periods: int,
    trend_context: dict[str, Any] | None = None,
) -> dict | None:
    """Lifecycle curve forecast with pytrends fallback."""
    if trend_context and trend_context.get("stage"):
        lifecycle = build_lifecycle_forecast(
            series,
            periods,
            stage=str(trend_context["stage"]),
            metrics=dict(trend_context.get("metrics") or {}),
            related_queries=trend_context.get("relatedQueries"),
            geo=str(trend_context.get("geo") or "ES"),
        )
        if lifecycle:
            return lifecycle

    related = trend_context.get("relatedQueries") if trend_context else None
    geo = str(trend_context.get("geo") or "ES") if trend_context else "ES"
    return build_pytrends_forecast(series, periods, related_queries=related, geo=geo)
