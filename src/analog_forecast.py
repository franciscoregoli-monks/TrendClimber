"""Find historical trend analogs via Gemini and build scaled forecast trajectories."""

from __future__ import annotations

import logging
import time
from typing import Any, TypedDict

import numpy as np
import pandas as pd

from src.keyword_generator import _get_model, _parse_json_response
from src.trends_fetcher import fetch_interest_over_time, today_date

logger = logging.getLogger(__name__)

MIN_MATCH_LEN = 10
MAX_MATCH_LEN = 30
MIN_CORRELATION = 0.5
ANALOG_FETCH_DELAY_S = 2.5

# Typical search-interest retention after a viral peak (empirical fad curve).
POST_PEAK_DECAY_RATIOS: list[float] = [
    0.92, 0.86, 0.80, 0.75, 0.70, 0.65, 0.60,
    0.55, 0.50, 0.46, 0.42, 0.38, 0.35, 0.32,
    0.29, 0.26, 0.24, 0.22, 0.20, 0.18, 0.16,
    0.15, 0.14, 0.13, 0.12, 0.11, 0.10, 0.09,
    0.08, 0.08,
]


class AnalogTrend(TypedDict):
    name: str
    keywords: list[str]
    similarity: str
    expectedPostPeak: str


class AnalogReference(TypedDict, total=False):
    name: str
    keywords: list[str]
    similarity: str
    correlation: float
    matchStart: str
    expectedPostPeak: str


ANALOG_PROMPT = """Eres un analista de tendencias culturales y Google Trends.

Te pasan el perfil de una tendencia ACTUAL. Tu tarea: proponer 1 tendencia histórica
(real, ocurrida en el pasado) que haya tenido una forma de curva SIMILAR en Google Trends
(especialmente si hay pico viral, crecimiento explosivo o ciclo fad).

Título actual: {title}
Descripción: {description}
Keywords actuales: {keywords}
Estadio del ciclo: {stage}
Métricas: growth_ratio={growth_ratio}, peak_position={peak_position}, volatility={volatility}
Interés reciente (últimos días): {recent_shape}

Reglas:
- Devuelve exactamente 1 analogía (la más útil para predecir los próximos 30 días).
- keywords: 1 término de búsqueda concreto en Google Trends (como lo buscaría la gente).
- Debe ser un fenómeno PASADO con datos en Trends (película viral, challenge, meme, producto hype).
- expectedPostPeak: qué suele pasar después del pico (declive gradual, meseta, segunda ola…).
- Responde en español.

Responde SOLO JSON válido:
{{
  "analogs": [
    {{
      "name": "Nombre del fenómeno histórico",
      "keywords": ["término trends"],
      "similarity": "Por qué la forma es parecida",
      "expectedPostPeak": "Comportamiento típico post-pico"
    }}
  ]
}}
"""


def _zscore(values: np.ndarray) -> np.ndarray:
    arr = values.astype(float)
    std = float(np.std(arr))
    if std < 1e-9:
        return arr - float(np.mean(arr))
    return (arr - float(np.mean(arr))) / std


def _normalize_to_peak(values: np.ndarray) -> np.ndarray:
    peak = max(float(np.max(values)), 1.0)
    return values.astype(float) / peak


def _describe_recent_shape(series: pd.Series, window: int = 14) -> str:
    values = series.values.astype(float)
    if len(values) < 5:
        return "serie corta"
    tail = values[-window:]
    head = values[-window * 2 : -window] if len(values) >= window * 2 else values[: len(values) // 2]
    tail_avg = float(np.mean(tail))
    head_avg = float(np.mean(head)) if len(head) else float(np.mean(values))
    ratio = tail_avg / max(head_avg, 1.0)
    if ratio > 2.5 and tail[-1] > head_avg * 2:
        return f"pico viral reciente (x{ratio:.1f} vs periodo previo)"
    if ratio > 1.4:
        return f"aceleración reciente (x{ratio:.1f})"
    if ratio < 0.7:
        return "caída reciente"
    return "evolución estable"


def is_spike_pattern(series: pd.Series) -> bool:
    values = series.values.astype(float)
    if len(values) < 7:
        return False
    recent_max = float(np.max(values[-7:]))
    baseline = float(np.mean(values[:-7])) if len(values) > 7 else float(np.mean(values))
    last = float(values[-1])
    return recent_max > max(baseline * 2.0, 8) and last > max(baseline * 1.5, 5)


def is_late_spike_series(series: pd.Series) -> bool:
    """Spike concentrated in the final portion of a long series (e.g. flat year + viral week)."""
    if not is_spike_pattern(series):
        return False
    values = series.values.astype(float)
    if len(values) < 21:
        return False
    peak_idx = int(np.argmax(values))
    peak_pos = peak_idx / max(len(values) - 1, 1)
    pre_peak = values[:peak_idx] if peak_idx > 0 else values[:1]
    pre_avg = float(np.mean(pre_peak)) if len(pre_peak) else 0.0
    peak_val = float(values[peak_idx])
    return peak_pos >= 0.72 and peak_val > max(pre_avg * 3, 15)


def recent_peak_value(series: pd.Series) -> float:
    values = series.values.astype(float)
    tail = values[-21:] if len(values) >= 21 else values
    return max(float(np.max(tail)), float(values[-1]), 1.0)


def find_analog_trends(
    *,
    title: str,
    description: str,
    keywords: list[str],
    stage: str,
    metrics: dict[str, Any],
    recent_series: pd.Series,
) -> AnalogTrend | None:
    try:
        model = _get_model()
        prompt = ANALOG_PROMPT.format(
            title=title,
            description=description,
            keywords=", ".join(keywords),
            stage=stage,
            growth_ratio=metrics.get("growth_ratio", "n/a"),
            peak_position=metrics.get("peak_position", "n/a"),
            volatility=metrics.get("volatility", "n/a"),
            recent_shape=_describe_recent_shape(recent_series),
        )
        response = model.generate_content(prompt)
        parsed = _parse_json_response(response.text)
        analogs = parsed.get("analogs") or []
        if not analogs:
            return None
        item = analogs[0]
        kw = [k.strip() for k in item.get("keywords", []) if k.strip()]
        if not kw:
            return None
        return AnalogTrend(
            name=str(item.get("name") or kw[0]),
            keywords=kw[:1],
            similarity=str(item.get("similarity") or ""),
            expectedPostPeak=str(item.get("expectedPostPeak") or ""),
        )
    except Exception as exc:
        logger.warning("Analog trend lookup failed: %s", exc)
        return None


def fetch_analog_series(keywords: list[str], geo: str = "ES") -> pd.Series:
    time.sleep(ANALOG_FETCH_DELAY_S)
    data = fetch_interest_over_time(keywords, geo=geo, timeframe="today 5-y")
    series = data.sum(axis=1).astype(float)
    series.index = pd.to_datetime(series.index).normalize()
    end = pd.Timestamp(today_date())
    return series[series.index <= end].sort_index()


def _best_match(analog: np.ndarray, template: np.ndarray, periods: int) -> tuple[int, float]:
    m = len(template)
    n = len(analog)
    if m < 5 or n < m + periods + 5:
        return -1, 0.0

    t_norm = _normalize_to_peak(template)
    t = _zscore(t_norm)
    global_peak = max(float(np.max(analog)), 1.0)

    best_i = -1
    best_r = -1.0
    for i in range(0, n - m - periods):
        window = analog[i : i + m]
        w_peak = max(float(np.max(window)), 1.0)
        if w_peak < global_peak * 0.25:
            continue

        w_norm = _normalize_to_peak(window)
        if float(np.std(w_norm)) < 1e-6:
            continue
        r = float(np.corrcoef(t, _zscore(w_norm))[0, 1])
        if np.isnan(r):
            continue

        future = analog[i + m : i + m + periods]
        if len(future) < max(7, periods // 3):
            continue
        # Reject matches whose post-window immediately flatlines at zero.
        if float(np.max(future[: min(5, len(future))])) < w_peak * 0.08:
            continue

        if r > best_r:
            best_r = r
            best_i = i
    return best_i, best_r


def _extend_tail(values: np.ndarray, periods: int, floor_ratio: float = 0.05) -> np.ndarray:
    if len(values) == 0:
        return np.full(periods, floor_ratio)
    if len(values) >= periods:
        return values[:periods]

    peak = max(float(np.max(values)), 1.0)
    out = list(values.astype(float))
    last = float(values[-1])
    for _ in range(periods - len(values)):
        last = max(last * 0.92, peak * floor_ratio)
        out.append(last)
    return np.array(out[:periods], dtype=float)


def build_decay_forecast(
    shape_series: pd.Series,
    periods: int,
    first_forecast_day: pd.Timestamp,
) -> list[dict]:
    peak = recent_peak_value(shape_series)
    ratios = (POST_PEAK_DECAY_RATIOS + [POST_PEAK_DECAY_RATIOS[-1]] * periods)[:periods]
    std = peak * 0.12

    rows: list[dict] = []
    for i, ratio in enumerate(ratios):
        ds = first_forecast_day + pd.Timedelta(days=i)
        pred = peak * ratio
        rows.append(
            {
                "date": ds.strftime("%Y-%m-%d"),
                "actual": None,
                "forecast": round(pred, 2),
                "lower": round(max(pred - 1.28 * std, 0), 2),
                "upper": round(min(pred + 1.28 * std, peak * 1.05), 2),
                "isFuture": True,
            }
        )
    return rows


def build_spike_decay_base_forecast(
    shape_series: pd.Series,
    periods: int,
    first_forecast_day: pd.Timestamp,
) -> dict:
    timeline = build_decay_forecast(shape_series, periods, first_forecast_day)
    return {
        "method": "spike_decay",
        "hasSeasonality": False,
        "forecastDays": periods,
        "forecastFrom": first_forecast_day.strftime("%Y-%m-%d"),
        "timeline": timeline,
        "seasonality": [],
        "label": "Post-peak decay model — calibrated for viral spike patterns",
    }


def build_analog_forecast(
    shape_series: pd.Series,
    analog: pd.Series,
    periods: int,
    first_forecast_day: pd.Timestamp,
) -> tuple[list[dict], float, int] | None:
    shape_series = shape_series.sort_index().astype(float)
    analog_vals = analog.sort_index().astype(float).values
    if len(analog_vals) < MIN_MATCH_LEN + periods + 5 or len(shape_series) < MIN_MATCH_LEN:
        return None

    match_len = min(MAX_MATCH_LEN, len(shape_series), 28)
    match_len = max(MIN_MATCH_LEN, match_len)
    template = shape_series.values[-match_len:].astype(float)

    start_idx, correlation = _best_match(analog_vals, template, periods)
    if start_idx < 0 or correlation < MIN_CORRELATION:
        return None

    anchor_idx = start_idx + match_len - 1
    future_start = anchor_idx + 1
    future_slice = analog_vals[future_start : future_start + periods]
    future_slice = _extend_tail(future_slice, periods)

    window_peak = max(float(np.max(analog_vals[start_idx : anchor_idx + 1])), 1.0)
    current_peak = recent_peak_value(shape_series)
    future_norm = _normalize_to_peak(future_slice) if window_peak > 0 else future_slice
    if window_peak > 0 and float(np.max(future_norm)) <= 1.0:
        scaled = current_peak * future_norm
    else:
        scaled = current_peak * (future_slice / window_peak)

    scaled = np.clip(scaled, 0, None)
    analog_std = max(float(np.std(scaled[: min(7, len(scaled))])), current_peak * 0.08, 1.0)

    rows: list[dict] = []
    for i in range(periods):
        ds = first_forecast_day + pd.Timedelta(days=i)
        pred = float(scaled[i])
        rows.append(
            {
                "date": ds.strftime("%Y-%m-%d"),
                "actual": None,
                "forecast": round(pred, 2),
                "lower": round(max(pred - 1.28 * analog_std, 0), 2),
                "upper": round(min(pred + 1.28 * analog_std, current_peak * 1.05), 2),
                "isFuture": True,
            }
        )
    return rows, correlation, start_idx


def _prophet_overcorrects(base_timeline: list[dict], last_actual: float) -> bool:
    if not base_timeline or last_actual <= 0:
        return False
    first = float(base_timeline[0]["forecast"])
    return first < last_actual * 0.55


def _blend_timelines(
    base: list[dict],
    analog: list[dict],
    *,
    analog_weight: float,
) -> list[dict]:
    base_weight = 1.0 - analog_weight
    blended: list[dict] = []
    for b, a in zip(base, analog):
        fc = base_weight * float(b["forecast"]) + analog_weight * float(a["forecast"])
        lo = base_weight * float(b["lower"]) + analog_weight * float(a["lower"])
        hi = base_weight * float(b["upper"]) + analog_weight * float(a["upper"])
        blended.append(
            {
                "date": b["date"],
                "actual": None,
                "forecast": round(max(fc, 0), 2),
                "lower": round(max(lo, 0), 2),
                "upper": round(max(hi, 0), 2),
                "isFuture": True,
            }
        )
    return blended


def apply_post_peak_floor(
    timeline: list[dict],
    shape_series: pd.Series,
) -> list[dict]:
    """Ensure forecast never collapses faster than a plausible fad decay."""
    peak = recent_peak_value(shape_series)
    ratios = (POST_PEAK_DECAY_RATIOS + [POST_PEAK_DECAY_RATIOS[-1]] * len(timeline))[: len(timeline)]
    adjusted: list[dict] = []
    for i, row in enumerate(timeline):
        floor = peak * ratios[i] * 0.85
        fc = max(float(row["forecast"]), floor)
        lo = max(float(row["lower"]), floor * 0.7)
        hi = max(float(row["upper"]), fc)
        adjusted.append(
            {
                **row,
                "forecast": round(fc, 2),
                "lower": round(lo, 2),
                "upper": round(min(hi, peak * 1.05), 2),
            }
        )
    return adjusted


def enhance_forecast_with_analog(
    shape_series: pd.Series,
    base_forecast: dict,
    *,
    title: str,
    description: str,
    keywords: list[str],
    stage: str,
    metrics: dict[str, Any],
    geo: str,
) -> dict:
    """Blend base forecast with a scaled historical analog curve."""
    if not base_forecast or not base_forecast.get("timeline"):
        return base_forecast

    spike = is_spike_pattern(shape_series) or float(metrics.get("growth_ratio", 1)) > 1.8
    if not spike:
        return base_forecast

    base_timeline = base_forecast["timeline"]
    last_actual = float(shape_series.iloc[-1])
    overcorrects = _prophet_overcorrects(base_timeline, last_actual)

    analog_meta = find_analog_trends(
        title=title,
        description=description,
        keywords=keywords,
        stage=stage,
        metrics=metrics,
        recent_series=shape_series,
    )

    first_day = pd.Timestamp(base_forecast["forecastFrom"])
    periods = int(base_forecast.get("forecastDays") or 30)
    analog_timeline: list[dict] | None = None
    correlation = 0.0
    match_idx = 0
    match_date: str | None = None
    name = "decay model"
    analog_keywords: list[str] = []

    if analog_meta:
        name = analog_meta["name"]
        analog_keywords = analog_meta["keywords"]
        try:
            analog_series = fetch_analog_series(analog_meta["keywords"], geo=geo)
            built = build_analog_forecast(shape_series, analog_series, periods, first_day)
            if built:
                analog_timeline, correlation, match_idx = built
                match_date = pd.Timestamp(analog_series.index[match_idx]).strftime("%Y-%m-%d")
        except Exception as exc:
            logger.warning("Analog series fetch failed: %s", exc)

    if analog_timeline is None:
        analog_timeline = build_decay_forecast(shape_series, periods, first_day)

    if overcorrects or base_forecast.get("method") in ("moving_average", "prophet"):
        # Base model reverts to long-run mean after a late spike — trust shape/analog more.
        blended = analog_timeline
        analog_weight = 1.0
    elif base_forecast.get("method") == "spike_decay":
        analog_weight = 0.55 if correlation >= 0.55 else 0.4
        blended = _blend_timelines(base_timeline, analog_timeline, analog_weight=analog_weight)
    elif analog_timeline:
        analog_weight = 0.75 if correlation >= 0.65 else 0.6
        blended = _blend_timelines(base_timeline, analog_timeline, analog_weight=analog_weight)
    else:
        blended = base_timeline
        analog_weight = 0.0

    blended = apply_post_peak_floor(blended, shape_series)

    base_method = base_forecast.get("method", "moving_average")
    base_label = base_forecast.get("label", base_method)

    result: dict[str, Any] = {
        **base_forecast,
        "method": "analog_blend",
        "baseMethod": base_method,
        "timeline": blended,
        "label": (
            f"Analog + {base_label.split('—')[0].strip()} — "
            f"patrón: {name}"
            + (f" (r={correlation:.2f})" if correlation > 0 else " + decay curve")
        ),
        "blendWeights": {
            "base": round(1 - analog_weight, 2),
            "analog": round(analog_weight, 2),
        },
    }

    if analog_meta:
        result["analog"] = AnalogReference(
            name=name,
            keywords=analog_keywords,
            similarity=analog_meta["similarity"],
            correlation=round(correlation, 3),
            matchStart=match_date or "",
            expectedPostPeak=analog_meta["expectedPostPeak"],
        )

    return result
