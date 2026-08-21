"""Fallback trend curves when Google Trends rate-limits requests."""

from __future__ import annotations

from datetime import datetime, timedelta

import numpy as np
import pandas as pd

from src.trends_fetcher import today_date


def _spike_values(n: int, *, peak: float = 100.0) -> np.ndarray:
    """Viral fad shape: flat baseline then sharp spike at the end."""
    values = np.zeros(n, dtype=float)
    spike_len = max(8, n // 10)
    start = n - spike_len
    ramp = np.linspace(0.05, 1.0, spike_len)
    values[start:] = peak * ramp
    values[-1] *= 0.82
    return values


def build_demo_multi_window(
    keywords: list[str],
    geo: str = "ES",
) -> tuple[list[dict], pd.DataFrame, str, dict[str, pd.Series]]:
    """Synthetic 1Y / 30D / 7D windows for demo when pytrends is unavailable."""
    end = today_date()
    end_str = end.strftime("%Y-%m-%d")
    start_year = end - timedelta(days=364)
    start_30 = end - timedelta(days=29)
    start_7 = end - timedelta(days=6)

    dates = pd.date_range(start=start_year, end=end, freq="D")
    values = _spike_values(len(dates), peak=127.0 if geo == "AR" else 95.0)
    series_year = pd.Series(values, index=dates)
    series_30 = series_year[series_year.index >= pd.Timestamp(start_30)]
    series_7 = series_year[series_year.index >= pd.Timestamp(start_7)]

    year_map = {ts.strftime("%Y-%m-%d"): round(float(v), 2) for ts, v in series_year.items()}
    day30_map = {ts.strftime("%Y-%m-%d"): round(float(v), 2) for ts, v in series_30.items()}
    start_7_str = start_7.strftime("%Y-%m-%d")
    start_30_str = start_30.strftime("%Y-%m-%d")
    all_dates = sorted(set(year_map.keys()) | set(day30_map.keys()))

    timeline: list[dict] = []
    for date_str in all_dates:
        point: dict = {
            "date": date_str,
            "year": year_map.get(date_str),
            "days30": None,
            "days7": None,
        }
        if date_str in day30_map and date_str >= start_30_str:
            point["days30"] = day30_map[date_str]
        if date_str in day30_map and date_str >= start_7_str:
            point["days7"] = day30_map[date_str]
        timeline.append(point)

    classify_data = pd.DataFrame({"total": series_30})
    series_by_window = {
        "year": series_year,
        "days30": series_30,
        "days7": series_7,
    }
    return timeline, classify_data, end_str, series_by_window


def demo_related_queries(keyword: str) -> dict[str, list[dict[str, str | int]]]:
    seed = keyword.strip().lower()
    if "farmear" in seed and "aura" in seed:
        return {
            "top": [
                {"query": "que farmear aura", "value": 100},
                {"query": "farmear aura que significa", "value": 52},
            ],
            "rising": [
                {"query": "farmear aura qué es", "value": 382150},
                {"query": "farmear aura batalla", "value": 221550},
            ],
        }
    return {"top": [], "rising": []}
