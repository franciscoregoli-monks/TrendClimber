"""Fetch Google Trends interest-over-time data via pytrends."""

import hashlib
import os
import time
from datetime import datetime, timedelta
from typing import Any
from urllib.parse import urlparse

import numpy as np
import pandas as pd
from pytrends.request import TrendReq

PROPHET_FORECAST_DAYS = 7
CACHE_TTL_S = 900
CACHE_STALE_TTL_S = 6 * 3600
MAX_INTEREST_RETRIES = 2
RATE_LIMIT_RETRY_DELAYS = (8.0, 20.0)
MAX_DAILY_RANGE_DAYS = 269
PYTRENDS_TIMEOUT = (10, 25)
PYTRENDS_RETRIES = 2
PYTRENDS_BACKOFF_FACTOR = 0.1

_interest_cache: dict[str, tuple[float, pd.DataFrame]] = {}
_related_cache: dict[str, tuple[float, dict[str, list[dict[str, str | int]]]]] = {}


def _default_timeframe(days: int = 90) -> str:
    end = datetime.now()
    start = end - timedelta(days=min(days, MAX_DAILY_RANGE_DAYS))
    return f"{start.strftime('%Y-%m-%d')} {end.strftime('%Y-%m-%d')}"


def _friendly_error(exc: Exception) -> str:
    msg = str(exc).lower()
    if _is_rate_limit(exc):
        return (
            "Google Trends limitó las solicitudes (rate limit). "
            "Espera 1-2 minutos e intenta de nuevo."
        )
    return str(exc)


def _is_rate_limit(exc: Exception) -> bool:
    msg = str(exc).lower()
    if "429" in msg or "too many" in msg or "rate limit" in msg:
        return True
    resp = getattr(exc, "response", None)
    return resp is not None and getattr(resp, "status_code", None) == 429


def _mark_rate_limited() -> None:
    """Kept for compatibility; global cooldown removed to avoid multi-minute hangs."""
    return


def _wait_rate_limit_cooldown() -> None:
    return


def _retry_delay(exc: Exception, attempt: int) -> float:
    if _is_rate_limit(exc):
        _mark_rate_limited()
        idx = min(attempt, len(RATE_LIMIT_RETRY_DELAYS) - 1)
        return RATE_LIMIT_RETRY_DELAYS[idx]
    return float(2**attempt * 2)


def _cache_key(prefix: str, keywords: list[str], geo: str, timeframe: str) -> str:
    raw = f"{prefix}|{geo}|{timeframe}|{'|'.join(sorted(k.lower() for k in keywords))}"
    return hashlib.sha256(raw.encode()).hexdigest()


def _read_cache(
    cache: dict[str, tuple[float, Any]],
    key: str,
    *,
    allow_stale: bool = False,
) -> Any | None:
    entry = cache.get(key)
    if not entry:
        return None
    ts, value = entry
    age = time.time() - ts
    if age <= CACHE_TTL_S:
        return value
    if allow_stale and age <= CACHE_STALE_TTL_S:
        return value
    return None


def _write_cache(cache: dict[str, tuple[float, Any]], key: str, value: Any) -> None:
    cache[key] = (time.time(), value)


def today_date() -> datetime:
    """Current calendar day for trends data (includes partial/incomplete day)."""
    return datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)


def yesterday_date() -> datetime:
    """Previous complete day — kept for callers that still need it."""
    return today_date() - timedelta(days=1)


def _sum_series(data: pd.DataFrame) -> pd.Series:
    return data.sum(axis=1).astype(float)


def _trim_until_date(series: pd.Series, end: datetime) -> pd.Series:
    end_ts = pd.Timestamp(end)
    normalized = series.copy()
    normalized.index = pd.to_datetime(normalized.index).normalize()
    return normalized[normalized.index <= end_ts]


def fetch_multi_window_curves(
    keywords: list[str],
    geo: str = "ES",
    hl: str = "es-ES",
) -> tuple[list[dict], pd.DataFrame, str, dict[str, pd.Series]]:
    """
    Fetch summed keyword interest for 7d, 30d and 1y windows ending today.

    Returns:
        timeline: chart points with year / days30 / days7 fields
        classify_data: daily 30-day DataFrame for lifecycle classification
        data_until: today date string (YYYY-MM-DD)
        series_by_window: raw summed series per window
    """
    end = today_date()
    end_str = end.strftime("%Y-%m-%d")
    start_30 = end - timedelta(days=29)
    start_7 = end - timedelta(days=6)
    # Trends agrega por semana si el rango supera ~270 días; las ventanas 30D/7D
    # y el clasificador necesitan puntos diarios.
    start_year = end - timedelta(days=MAX_DAILY_RANGE_DAYS)

    tf_year = f"{start_year.strftime('%Y-%m-%d')} {end_str}"

    # Una sola llamada a Trends y recortamos ventanas 30D / 7D localmente.
    data_year = fetch_interest_over_time(keywords, geo=geo, timeframe=tf_year, hl=hl)
    series_year = _trim_until_date(_sum_series(data_year), end)
    series_30 = series_year[series_year.index >= pd.Timestamp(start_30)]
    series_7 = series_year[series_year.index >= pd.Timestamp(start_7)]

    year_map = {
        ts.strftime("%Y-%m-%d"): round(float(val), 2)
        for ts, val in series_year.items()
    }
    day30_map = {
        ts.strftime("%Y-%m-%d"): round(float(val), 2)
        for ts, val in series_30.items()
    }

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


def _https_proxies_from_env() -> list[str]:
    """Read optional comma-separated HTTPS proxies without accepting unsafe schemes."""
    raw = os.getenv("PYTRENDS_HTTPS_PROXIES", "")
    proxies: list[str] = []
    for value in raw.split(","):
        proxy = value.strip()
        if not proxy:
            continue
        parsed = urlparse(proxy)
        if parsed.scheme != "https" or not parsed.hostname or parsed.port is None:
            raise ValueError(
                "PYTRENDS_HTTPS_PROXIES debe contener URLs HTTPS con puerto."
            )
        proxies.append(proxy)
    return proxies


def _create_pytrend(hl: str = "es-ES") -> TrendReq:
    """Create a bounded pytrends client, optionally rotating configured proxies."""
    return TrendReq(
        hl=hl,
        tz=360,
        timeout=PYTRENDS_TIMEOUT,
        proxies=_https_proxies_from_env(),
        retries=PYTRENDS_RETRIES,
        backoff_factor=PYTRENDS_BACKOFF_FACTOR,
    )


def fetch_related_queries(
    keyword: str,
    geo: str = "ES",
    hl: str = "es-ES",
    timeframe: str | None = None,
    max_retries: int = 2,
) -> dict[str, list[dict[str, str | int]]]:
    """
    Fetch related search queries from Google Trends for a single keyword.

    Returns:
        {"top": [{"query": str, "value": int}, ...], "rising": [...]}
    """
    seed = keyword.strip()
    if not seed:
        raise ValueError("Se requiere una keyword semilla para related_queries.")

    tf = timeframe or _default_timeframe(90)
    cache_key = _cache_key("related", [seed], geo, tf)
    cached = _read_cache(_related_cache, cache_key)
    if cached is not None:
        return cached

    last_error: Exception | None = None

    for attempt in range(max_retries):
        try:
            pytrend = _create_pytrend(hl)
            pytrend.build_payload([seed], cat=0, timeframe=tf, geo=geo, gprop="")
            raw = pytrend.related_queries()
            bucket = raw.get(seed) if isinstance(raw, dict) else None
            if bucket is None and isinstance(raw, dict) and len(raw) == 1:
                bucket = next(iter(raw.values()))

            result: dict[str, list[dict[str, str | int]]] = {"top": [], "rising": []}
            if not bucket:
                _write_cache(_related_cache, cache_key, result)
                return result

            for kind in ("top", "rising"):
                frame = bucket.get(kind)
                if frame is None or frame.empty:
                    continue
                for _, row in frame.iterrows():
                    query = str(row.get("query", "")).strip()
                    if not query:
                        continue
                    value = row.get("value", 0)
                    if isinstance(value, str):
                        parsed: str | int = value
                    else:
                        try:
                            parsed = int(value)
                        except (TypeError, ValueError):
                            parsed = 0
                    result[kind].append({"query": query, "value": parsed})

            _write_cache(_related_cache, cache_key, result)
            return result
        except Exception as exc:
            last_error = exc
            if _is_rate_limit(exc):
                stale = _read_cache(_related_cache, cache_key, allow_stale=True)
                if stale is not None:
                    return stale
            if attempt < max_retries - 1:
                time.sleep(_retry_delay(exc, attempt))

    raise ValueError(_friendly_error(last_error)) from last_error


def extract_related_terms(
    related: dict[str, list[dict[str, str | int]]],
    *,
    max_rising: int = 3,
    max_top: int = 2,
) -> list[str]:
    """Pick the most useful related queries (rising first, then top)."""
    terms: list[str] = []
    seen: set[str] = set()

    def add(query: str) -> None:
        key = query.lower()
        if key in seen:
            return
        seen.add(key)
        terms.append(query)

    for item in related.get("rising", [])[:max_rising]:
        add(str(item["query"]))

    for item in related.get("top", [])[:max_top]:
        add(str(item["query"]))

    return terms


def _forecast_start_day(series: pd.Series) -> pd.Timestamp:
    last_hist = pd.Timestamp(series.index.max()).normalize()
    tomorrow = pd.Timestamp(today_date()) + pd.Timedelta(days=1)
    return max(tomorrow, last_hist + pd.Timedelta(days=1))


def _rising_momentum(related_queries: dict[str, Any] | None) -> tuple[float, str]:
    if not related_queries:
        return 1.0, ""
    rising = related_queries.get("rising") or []
    if not rising:
        return 1.0, ""
    item = rising[0]
    query = str(item.get("query", "")).strip()
    value = item.get("value", 0)
    if str(value).lower() == "breakout":
        return 1.25, query
    try:
        numeric = int(value)
        return 1.0 + min(numeric / 200.0, 0.35), query
    except (TypeError, ValueError):
        return 1.05, query


def build_pytrends_forecast(
    series: pd.Series,
    periods: int = PROPHET_FORECAST_DAYS,
    related_queries: dict[str, Any] | None = None,
    geo: str = "ES",
) -> dict | None:
    """
    Build a forward projection from Google Trends data (interest_over_time + related_queries).

    Uses the recent Trends slope and rising-query momentum from pytrends.related_queries().
    """
    series = series.sort_index().astype(float)
    if len(series) < 5:
        return None

    first_day = _forecast_start_day(series)
    window = min(14, len(series))
    recent = series.values[-window:].astype(float)
    x = np.arange(window)
    slope = float(np.polyfit(x, recent, 1)[0]) if window >= 2 else 0.0
    last = float(recent[-1])
    std = float(np.std(recent)) if window > 1 else max(last * 0.1, 1.0)

    momentum, rising_query = _rising_momentum(related_queries)
    slope *= momentum

    rising_slope: float | None = None
    if rising_query:
        try:
            end = today_date()
            start = end - timedelta(days=29)
            tf = f"{start.strftime('%Y-%m-%d')} {end.strftime('%Y-%m-%d')}"
            rising_data = fetch_interest_over_time([rising_query], geo=geo, timeframe=tf)
            rising_series = _trim_until_date(_sum_series(rising_data), end).values.astype(float)
            if len(rising_series) >= 5:
                rw = rising_series[-window:]
                rising_slope = float(np.polyfit(np.arange(len(rw)), rw, 1)[0]) * momentum
        except Exception:
            rising_slope = None

    timeline: list[dict] = []
    for i in range(periods):
        ds = first_day + pd.Timedelta(days=i)
        if rising_slope is not None:
            pred = last + rising_slope * (i + 1)
        else:
            pred = last + slope * (i + 1)
        pred = max(0.0, min(float(pred), 100.0))
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

    label = "Google Trends projection (recent interest"
    if rising_query:
        label += f" + rising query: {rising_query}"
    label += ")"

    return {
        "method": "pytrends",
        "hasSeasonality": False,
        "forecastDays": periods,
        "forecastFrom": first_day.strftime("%Y-%m-%d"),
        "timeline": timeline,
        "seasonality": [],
        "label": label,
        "risingQuery": rising_query or None,
    }


def fetch_interest_over_time(
    keywords: list[str],
    geo: str = "ES",
    timeframe: str | None = None,
    hl: str = "es-ES",
    max_retries: int = MAX_INTEREST_RETRIES,
) -> pd.DataFrame:
    """
    Fetch daily Google Trends interest for up to 5 keywords.
    Returns a DataFrame indexed by date with one column per keyword.
    """
    if not keywords:
        raise ValueError("Se requiere al menos una keyword.")
    if len(keywords) > 5:
        keywords = keywords[:5]

    tf = timeframe or _default_timeframe(90)
    cache_key = _cache_key("interest", keywords, geo, tf)
    cached = _read_cache(_interest_cache, cache_key)
    if cached is not None:
        return cached.copy()

    last_error: Exception | None = None

    for attempt in range(max_retries):
        try:
            pytrend = _create_pytrend(hl)
            pytrend.build_payload(
                keywords,
                cat=0,
                timeframe=tf,
                geo=geo,
                gprop="",
            )
            data = pytrend.interest_over_time()

            if data.empty:
                raise ValueError(
                    "Google Trends no devolvió datos. Prueba con otras keywords o un rango más amplio."
                )

            if "isPartial" in data.columns:
                # Keep today's partial point in the series; drop flag column only.
                data = data.drop(columns=["isPartial"])

            _write_cache(_interest_cache, cache_key, data)
            return data
        except Exception as exc:
            last_error = exc
            if _is_rate_limit(exc):
                stale = _read_cache(_interest_cache, cache_key, allow_stale=True)
                if stale is not None:
                    return stale.copy()
            if attempt < max_retries - 1:
                time.sleep(_retry_delay(exc, attempt))

    raise ValueError(_friendly_error(last_error)) from last_error
