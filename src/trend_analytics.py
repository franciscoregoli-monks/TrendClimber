"""Prophet forecast, slope and moving-average trend analytics."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any

import numpy as np
import pandas as pd

from src.lifecycle_curve_models import build_forecast
from src.trends_fetcher import PROPHET_FORECAST_DAYS

logger = logging.getLogger(__name__)

WINDOW_MA_CONFIG = {
    "days7": {"short": 3, "long": 5},
    "days30": {"short": 7, "long": 14},
    "year": {"short": 4, "long": 12},
}

MA_WINDOW_BOUNDS = {
    "days7": (2, 4),
    "days30": (3, 14),
    "year": (4, 26),
}

SEASONALITY_THRESHOLD_RATIO = 0.08

EVOLUTION_LABELS = {
    "golden_cross": "Golden Cross — short MA crossed above long MA. Bullish momentum.",
    "death_cross": "Death Cross — short MA crossed below long MA. Losing traction.",
    "bullish": "Bullish trend — interest above moving averages with supportive structure.",
    "bearish": "Bearish trend — interest trading below moving averages.",
    "neutral": "Sideways — no clear direction from moving averages.",
}

EVOLUTION_STAGES = {
    "golden_cross": "Growth",
    "death_cross": "Declining",
    "bullish": "Emerging",
    "bearish": "Declining",
    "neutral": "Saturated",
}


@dataclass
class SeriesAnalytics:
    payload: dict


def _linear_slope(values: np.ndarray) -> float:
    if len(values) < 2:
        return 0.0
    x = np.arange(len(values))
    return float(np.polyfit(x, values, 1)[0])


def _compute_slope(series: pd.Series) -> dict:
    values = series.values.astype(float)
    n = len(values)
    slope = _linear_slope(values)
    avg = float(np.mean(values)) if n else 1.0
    pct = (slope / max(avg, 1e-6)) * 100

    threshold = max(avg * 0.01, 0.05)
    if slope > threshold:
        direction = "bullish"
        label = "Bullish slope — search interest is accelerating."
    elif slope < -threshold:
        direction = "bearish"
        label = "Bearish slope — search interest is losing momentum."
    else:
        direction = "flat"
        label = "Flat slope — interest is holding steady."

    return {
        "value": round(slope, 3),
        "pctPerPeriod": round(pct, 2),
        "direction": direction,
        "label": label,
    }


def _detect_cross(short: pd.Series, long: pd.Series) -> str | None:
    if len(short) < 2 or len(long) < 2:
        return None
    prev_diff = float(short.iloc[-2] - long.iloc[-2])
    curr_diff = float(short.iloc[-1] - long.iloc[-1])
    if prev_diff <= 0 < curr_diff:
        return "golden_cross"
    if prev_diff >= 0 > curr_diff:
        return "death_cross"
    return None


def _compute_moving_average(series: pd.Series, short_w: int, long_w: int) -> dict:
    n = len(series)
    long_w = min(long_w, max(2, n))
    short_w = min(short_w, max(2, long_w))

    sma_short = series.rolling(short_w, min_periods=1).mean()
    sma_long = series.rolling(long_w, min_periods=1).mean()

    last_value = float(series.iloc[-1])
    last_short = float(sma_short.iloc[-1])
    last_long = float(sma_long.iloc[-1])

    cross = _detect_cross(sma_short, sma_long)
    if cross:
        signal = cross
    elif last_short > last_long and last_value >= last_short:
        signal = "bullish"
    elif last_short < last_long and last_value <= last_short:
        signal = "bearish"
    else:
        signal = "neutral"

    return {
        "shortWindow": short_w,
        "longWindow": long_w,
        "signal": signal,
        "evolutionStage": EVOLUTION_STAGES[signal],
        "label": EVOLUTION_LABELS[signal],
        "lastShort": round(last_short, 2),
        "lastLong": round(last_long, 2),
        "priceVsShort": round(last_value - last_short, 2),
        "priceVsLong": round(last_value - last_long, 2),
    }


def _build_ma_chart(series: pd.Series, short_w: int, long_w: int) -> list[dict]:
    rows: list[dict] = []
    for idx in series.index:
        ts = pd.Timestamp(idx)
        rows.append(
            {
                "date": ts.strftime("%Y-%m-%d"),
                "value": round(float(series.loc[idx]), 2),
            }
        )
    return rows


def _today_date() -> datetime:
    return datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)


def _extract_seasonality(model, forecast_hist: pd.DataFrame) -> list[dict]:
    """Extract repeating weekly / yearly / daily patterns from a fitted Prophet model."""
    components: list[dict] = []
    df = forecast_hist.copy()
    df["ds"] = pd.to_datetime(df["ds"])

    if model.weekly_seasonality and "weekly" in df.columns:
        dow_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        df["dow"] = df["ds"].dt.dayofweek
        points = []
        for dow, name in enumerate(dow_names):
            vals = df.loc[df["dow"] == dow, "weekly"]
            points.append(
                {
                    "label": name,
                    "value": round(float(vals.mean()), 3) if len(vals) else 0.0,
                }
            )
        components.append(
            {
                "type": "weekly",
                "title": "Weekly seasonality",
                "description": "How interest tends to shift across days of the week.",
                "points": points,
            }
        )

    if model.yearly_seasonality and "yearly" in df.columns:
        month_names = [
            "Jan", "Feb", "Mar", "Apr", "May", "Jun",
            "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
        ]
        df["month"] = df["ds"].dt.month
        points = []
        for month, name in enumerate(month_names, start=1):
            vals = df.loc[df["month"] == month, "yearly"]
            points.append(
                {
                    "label": name,
                    "value": round(float(vals.mean()), 3) if len(vals) else 0.0,
                }
            )
        components.append(
            {
                "type": "yearly",
                "title": "Yearly seasonality",
                "description": "Seasonal peaks and troughs across months of the year.",
                "points": points,
            }
        )

    if model.daily_seasonality and "daily" in df.columns:
        df["hour"] = df["ds"].dt.hour
        points = []
        for hour in range(24):
            vals = df.loc[df["hour"] == hour, "daily"]
            if len(vals) == 0:
                continue
            points.append(
                {
                    "label": f"{hour:02d}h",
                    "value": round(float(vals.mean()), 3),
                }
            )
        if points:
            components.append(
                {
                    "type": "daily",
                    "title": "Daily seasonality",
                    "description": "Intra-day repeating pattern (when hourly data is available).",
                    "points": points,
                }
            )

    return components


def _seasonality_is_significant(components: list[dict], series: pd.Series) -> bool:
    if not components:
        return False
    y_mean = max(float(series.mean()), 1.0)
    threshold = max(y_mean * SEASONALITY_THRESHOLD_RATIO, 0.5)
    for comp in components:
        values = [p["value"] for p in comp["points"]]
        if values and (max(values) - min(values)) >= threshold:
            return True
    return False


def _seasonality_method_label(components: list[dict]) -> str:
    names = {"weekly": "weekly", "yearly": "yearly", "daily": "daily"}
    parts = [names.get(c["type"], c["type"]) for c in components]
    return f"Prophet ({' + '.join(parts)} seasonality detected)"


def _find_best_ma_window(
    series: pd.Series,
    min_w: int,
    max_w: int,
) -> int:
    values = series.values.astype(float)
    n = len(values)
    max_w = min(max_w, max(min_w, n // 2))
    max_w = max(min_w, max_w)

    val_size = max(3, n // 5)
    train_end = n - val_size
    if train_end <= min_w:
        return min(max(min_w, 2), n // 2 or 2)

    best_w = min_w
    best_mse = float("inf")
    for w in range(min_w, max_w + 1):
        mse_sum = 0.0
        count = 0
        for t in range(train_end, n):
            if t < w:
                continue
            pred = float(np.mean(values[t - w : t]))
            mse_sum += (pred - values[t]) ** 2
            count += 1
        if count and (mse_sum / count) < best_mse:
            best_mse = mse_sum / count
            best_w = w
    return best_w


def _first_forecast_day(series: pd.Series) -> pd.Timestamp:
    today = pd.Timestamp(_today_date())
    last_hist_day = pd.Timestamp(series.index.max()).normalize()
    return max(today, last_hist_day + pd.Timedelta(days=1))


def _ma_forecast(series: pd.Series, periods: int, window: int) -> tuple[list[dict], str]:
    values = series.values.astype(float)
    first_forecast_day = _first_forecast_day(series)

    sma = pd.Series(values).rolling(window, min_periods=1).mean()
    residuals = values - sma.values
    tail = residuals[-window:] if len(residuals) >= window else residuals
    std = float(np.std(tail)) if len(tail) > 1 else float(np.std(values) or 1.0)

    sma_vals = sma.values
    tail_len = min(window, len(sma_vals))
    sma_slope = _linear_slope(sma_vals[-tail_len:]) if tail_len >= 2 else _linear_slope(values)
    last_sma = float(sma.iloc[-1])

    rows: list[dict] = []
    for i in range(periods):
        ds = first_forecast_day + pd.Timedelta(days=i)
        pred = max(last_sma + sma_slope * (i + 1), 0)
        rows.append(
            {
                "date": ds.strftime("%Y-%m-%d"),
                "actual": None,
                "forecast": round(pred, 2),
                "lower": round(max(pred - 1.28 * std, 0), 2),
                "upper": round(pred + 1.28 * std, 2),
                "isFuture": True,
            }
        )
    return rows, first_forecast_day.strftime("%Y-%m-%d")


def _try_prophet(series: pd.Series, periods: int) -> dict | None:
    """Fit Prophet and test whether seasonality is strong enough to forecast with."""
    if len(series) < 5:
        return None

    try:
        from prophet import Prophet

        logging.getLogger("cmdstanpy").setLevel(logging.ERROR)
        logging.getLogger("prophet").setLevel(logging.ERROR)

        history = pd.DataFrame(
            {
                "ds": pd.to_datetime(series.index),
                "y": series.values.astype(float),
            }
        )
        history["y"] = history["y"].clip(lower=0)
        last_hist = history["ds"].max()

        weekly = len(series) >= 14
        yearly = len(series) > 120
        daily = len(series) <= 60

        model = Prophet(
            daily_seasonality=daily,
            weekly_seasonality=weekly,
            yearly_seasonality=yearly,
            interval_width=0.8,
        )
        model.fit(history)

        future = model.predict(model.make_future_dataframe(periods=periods))
        hist_forecast = future[future["ds"] <= last_hist]
        components = _extract_seasonality(model, hist_forecast)
        has_seasonality = _seasonality_is_significant(components, series)

        first_forecast_day = _first_forecast_day(series)
        timeline: list[dict] = []
        for _, row in future.iterrows():
            ds = pd.Timestamp(row["ds"]).normalize()
            if ds < first_forecast_day:
                continue
            timeline.append(
                {
                    "date": ds.strftime("%Y-%m-%d"),
                    "actual": None,
                    "forecast": round(max(float(row["yhat"]), 0), 2),
                    "lower": round(max(float(row["yhat_lower"]), 0), 2),
                    "upper": round(max(float(row["yhat_upper"]), 0), 2),
                    "isFuture": True,
                }
            )

        if not timeline:
            return None

        label = (
            _seasonality_method_label(components)
            if has_seasonality
            else f"Prophet · proyección a {periods} días"
        )

        return {
            "hasSeasonality": has_seasonality,
            "forecastFrom": first_forecast_day.strftime("%Y-%m-%d"),
            "timeline": timeline,
            "seasonality": components if has_seasonality else [],
            "label": label,
        }
    except Exception as exc:
        logger.warning("Prophet fit failed: %s", exc)
        return None


def _build_forecast(
    series: pd.Series,
    periods: int,
    trend_context: dict[str, Any] | None = None,
) -> dict | None:
    prophet = _try_prophet(series, periods)
    if prophet:
        label = prophet.get("label") or f"Prophet · proyección a {periods} días"
        forecast = {
            "method": "prophet",
            "hasSeasonality": prophet["hasSeasonality"],
            "forecastDays": periods,
            "forecastFrom": prophet["forecastFrom"],
            "timeline": prophet["timeline"],
            "seasonality": prophet["seasonality"],
            "label": label,
        }
        return _align_forecast_with_lifecycle(forecast, series, trend_context)

    forecast = build_forecast(series, periods, trend_context)
    return _align_forecast_with_lifecycle(forecast, series, trend_context)


def _align_forecast_with_lifecycle(
    forecast: dict | None,
    series: pd.Series,
    trend_context: dict[str, Any] | None,
) -> dict | None:
    """Avoid an unsupported rebound when the global curve is clearly declining."""
    if not forecast or not trend_context:
        return forecast
    metrics = trend_context.get("metrics") or {}
    clearly_declining = (
        trend_context.get("stage") == "En declive"
        and float(metrics.get("current_to_peak", 1.0)) <= 0.35
        and float(metrics.get("momentum_30", 0.0)) <= 0
    )
    if not clearly_declining or forecast.get("hasSeasonality"):
        return forecast

    ceiling = max(float(series.dropna().iloc[-1]), 0.0)
    adjusted = {**forecast, "timeline": []}
    for point in forecast.get("timeline", []):
        row = dict(point)
        prediction = min(max(float(row.get("forecast") or 0), 0.0), ceiling)
        row["forecast"] = round(prediction, 2)
        row["lower"] = round(
            min(max(float(row.get("lower") or 0), 0.0), prediction),
            2,
        )
        row["upper"] = round(
            min(max(float(row.get("upper") or prediction), prediction), ceiling),
            2,
        )
        adjusted["timeline"].append(row)
        ceiling = prediction

    adjusted["label"] = (
        f"{forecast.get('label', 'Proyección')} · coherente con el declive observado"
    )
    return adjusted


def _select_training_series(series_by_window: dict[str, pd.Series]) -> pd.Series | None:
    days30 = series_by_window.get("days30")
    if days30 is not None and len(days30) >= 5:
        return days30
    for key in ("year", "days7"):
        series = series_by_window.get(key)
        if series is not None and len(series) >= 5:
            return series
    return None


def analyze_series(series: pd.Series, window_key: str) -> dict | None:
    if series is None or len(series) < 5:
        return None

    series = series.sort_index().astype(float)
    config = WINDOW_MA_CONFIG.get(window_key, WINDOW_MA_CONFIG["days30"])

    slope = _compute_slope(series)
    ma = _compute_moving_average(series, config["short"], config["long"])
    ma_chart = _build_ma_chart(series, config["short"], config["long"])

    return {
        "slope": slope,
        "movingAverage": ma,
        "maChart": ma_chart,
    }


def analyze_all_windows(
    series_by_window: dict[str, pd.Series],
    trend_context: dict | None = None,
) -> tuple[dict, dict | None]:
    analytics: dict = {}
    for key, series in series_by_window.items():
        result = analyze_series(series, key)
        if result:
            analytics[key] = result

    train = _select_training_series(series_by_window)
    forecast = (
        _build_forecast(train, PROPHET_FORECAST_DAYS, trend_context)
        if train is not None
        else None
    )
    return analytics, forecast
