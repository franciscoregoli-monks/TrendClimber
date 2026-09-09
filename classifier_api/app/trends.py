"""Fetch Google Trends interest-over-time for a single trend keyword."""

from __future__ import annotations

import hashlib
import time
from datetime import datetime, timedelta

import pandas as pd
from pytrends.request import TrendReq

CACHE_TTL_S = 900
CACHE_STALE_TTL_S = 6 * 3600
MAX_RETRIES = 2
RATE_LIMIT_RETRY_DELAYS = (8.0, 20.0)

_interest_cache: dict[str, tuple[float, pd.DataFrame]] = {}


def _is_rate_limit(exc: Exception) -> bool:
    msg = str(exc).lower()
    if "429" in msg or "too many" in msg or "rate limit" in msg:
        return True
    resp = getattr(exc, "response", None)
    return resp is not None and getattr(resp, "status_code", None) == 429


def _friendly_error(exc: Exception) -> str:
    if _is_rate_limit(exc):
        return (
            "Google Trends limitó las solicitudes (rate limit). "
            "Espera 1-2 minutos e intenta de nuevo."
        )
    return str(exc)


def _cache_key(keywords: list[str], geo: str, timeframe: str) -> str:
    raw = f"{geo}|{timeframe}|{'|'.join(k.lower() for k in keywords)}"
    return hashlib.sha256(raw.encode()).hexdigest()


def _read_cache(key: str, *, allow_stale: bool = False) -> pd.DataFrame | None:
    entry = _interest_cache.get(key)
    if not entry:
        return None
    ts, value = entry
    age = time.time() - ts
    if age <= CACHE_TTL_S or (allow_stale and age <= CACHE_STALE_TTL_S):
        return value.copy()
    return None


def fetch_trend_series(
    keywords: list[str],
    geo: str = "ES",
    hl: str = "es-ES",
) -> tuple[pd.DataFrame, pd.Series]:
    """Fetch ~90 days of interest. Returns (30-day frame for stage, full series for curve)."""
    keywords = [k.strip() for k in keywords if k.strip()][:5]
    if not keywords:
        raise ValueError("Se requiere al menos una keyword.")

    end = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    # ≤269 días para que Google Trends devuelva serie diaria (no semanal).
    start = end - timedelta(days=90)
    timeframe = f"{start.strftime('%Y-%m-%d')} {end.strftime('%Y-%m-%d')}"
    key = _cache_key(keywords, geo, timeframe)

    cached = _read_cache(key)
    if cached is None:
        last_error: Exception | None = None
        for attempt in range(MAX_RETRIES):
            try:
                pytrend = TrendReq(hl=hl, tz=360, retries=2, backoff_factor=1.5)
                pytrend.build_payload(keywords, cat=0, timeframe=timeframe, geo=geo, gprop="")
                data = pytrend.interest_over_time()
                if data.empty:
                    raise ValueError(
                        "Google Trends no devolvió datos. Prueba con otro nombre de trend o región."
                    )
                if "isPartial" in data.columns:
                    data = data.drop(columns=["isPartial"])
                _interest_cache[key] = (time.time(), data)
                cached = data.copy()
                break
            except Exception as exc:
                last_error = exc
                if _is_rate_limit(exc):
                    stale = _read_cache(key, allow_stale=True)
                    if stale is not None:
                        cached = stale
                        break
                if attempt < MAX_RETRIES - 1:
                    delay = RATE_LIMIT_RETRY_DELAYS[min(attempt, len(RATE_LIMIT_RETRY_DELAYS) - 1)]
                    time.sleep(delay)
        if cached is None:
            raise ValueError(_friendly_error(last_error)) from last_error

    series = cached.sum(axis=1).astype(float)
    series.index = pd.to_datetime(series.index).normalize()
    series = series[series.index <= pd.Timestamp(end)]
    start_30 = end - timedelta(days=29)
    series_30 = series[series.index >= pd.Timestamp(start_30)]
    classify_data = pd.DataFrame({"total": series_30})
    return classify_data, series
