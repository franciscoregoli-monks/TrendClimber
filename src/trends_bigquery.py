"""Fetch suggested trends from BigQuery (X / Google Trends raw feed)."""

from __future__ import annotations

import os
import time
from datetime import date
from typing import Any

from dotenv import load_dotenv

load_dotenv()

DEFAULT_TABLE = "mm-trends-agent.010_raw.raw_x_trends"
DEFAULT_PROJECT = "mm-trends-agent"
DEFAULT_LIMIT = 12

_GEO_TO_COUNTRY: dict[str, list[str]] = {
    "ES": ["ES", "ESP", "ESPAÑA", "SPAIN"],
    "AR": ["AR", "ARG", "ARGENTINA"],
    "MX": ["MX", "MEX", "MÉXICO", "MEXICO"],
}

_CACHE: dict[str, tuple[float, list[dict[str, Any]]]] = {}
_CACHE_TTL_SECONDS = 300


def _table_id() -> str:
    return os.getenv("BQ_TRENDS_TABLE", DEFAULT_TABLE)


def _project_id() -> str:
    return os.getenv("BQ_PROJECT_ID", DEFAULT_PROJECT)


def _min_load_date() -> str:
    return os.getenv("BQ_MIN_LOAD_DATE", date.today().isoformat())


def _country_filter(geo: str) -> list[str]:
    geo = (geo or "").strip().upper()
    if not geo:
        return []
    return _GEO_TO_COUNTRY.get(geo, [geo])


def _row_to_trend(row: Any) -> dict[str, Any]:
    urls = []
    for item in row.urls or []:
        urls.append(
            {
                "title": getattr(item, "title", None),
                "uri": getattr(item, "uri", None),
                "domain": getattr(item, "domain", None),
            }
        )

    metrics = []
    for item in row.metrics or []:
        metrics.append(
            {
                "name": getattr(item, "name", None),
                "description": getattr(item, "description", None),
                "value": getattr(item, "value", None),
            }
        )

    ingested = row.ingested_at
    load_date = row.load_date

    return {
        "trend": row.trend,
        "trendDescription": row.trend_description,
        "trendSource": getattr(row, "trend_source", None) or "x-trends",
        "trendSignal": getattr(row, "trend_signal", None) or "",
        "country": getattr(row, "country", None) or "",
        "language": getattr(row, "language", None),
        "loadDate": load_date.isoformat() if load_date else None,
        "ingestedAt": ingested.isoformat() if ingested else None,
        "urls": urls,
        "metrics": metrics,
    }


def _run_query(
    client: Any,
    *,
    geo: str,
    limit: int,
    min_load_date: str,
    countries: list[str],
) -> list[dict[str, Any]]:
    from google.cloud import bigquery

    country_clause = ""
    params: list[Any] = [
        bigquery.ScalarQueryParameter("min_load_date", "DATE", min_load_date),
        bigquery.ScalarQueryParameter("limit", "INT64", limit),
    ]

    if countries:
        country_clause = "AND UPPER(country) IN UNNEST(@countries)"
        params.insert(1, bigquery.ArrayQueryParameter("countries", "STRING", [c.upper() for c in countries]))

    query = f"""
        SELECT
          trend,
          trend_description,
          trend_source,
          trend_signal,
          country,
          language,
          load_date,
          ingested_at,
          urls,
          metrics
        FROM (
          SELECT
            *,
            ROW_NUMBER() OVER (
              PARTITION BY trend, trend_description
              ORDER BY load_date DESC, ingested_at DESC
            ) AS rn
          FROM `{_table_id()}`
          WHERE load_date >= @min_load_date
          {country_clause}
        )
        WHERE rn = 1
        ORDER BY load_date DESC, ingested_at DESC
        LIMIT @limit
    """

    rows = client.query(query, job_config=bigquery.QueryJobConfig(query_parameters=params)).result()
    return [_row_to_trend(row) for row in rows]


def fetch_suggested_trends(
    *,
    geo: str = "",
    limit: int = DEFAULT_LIMIT,
) -> list[dict[str, Any]]:
    """
    Return distinct trends from raw_x_trends where load_date >= min date.

    Default query shape:
      SELECT DISTINCT trend_description, trend
      FROM raw_x_trends
      WHERE load_date >= @min_load_date

    Uses Application Default Credentials or GOOGLE_APPLICATION_CREDENTIALS.
    """
    limit = max(1, min(limit, 50))
    min_load_date = _min_load_date()
    cache_key = f"{geo.upper()}:{limit}:{min_load_date}"
    cached = _CACHE.get(cache_key)
    now = time.time()
    if cached and now - cached[0] < _CACHE_TTL_SECONDS:
        return cached[1]

    try:
        from google.cloud import bigquery
    except ImportError as exc:
        raise RuntimeError(
            "google-cloud-bigquery no está instalado. Ejecuta: pip install google-cloud-bigquery"
        ) from exc

    client = bigquery.Client(project=_project_id())
    countries = _country_filter(geo)

    try:
        trends = _run_query(
            client,
            geo=geo,
            limit=limit,
            min_load_date=min_load_date,
            countries=countries,
        )
    except Exception as exc:
        raise RuntimeError(f"Error al consultar BigQuery: {exc}") from exc

    if not trends and countries:
        trends = fetch_suggested_trends(geo="", limit=limit)

    _CACHE[cache_key] = (now, trends)
    return trends
