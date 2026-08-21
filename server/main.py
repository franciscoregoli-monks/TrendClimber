"""FastAPI backend for TrendClimber — wraps existing Python modules."""

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from src.brand_strategy import generate_brand_strategy, summarize_analyze_response
from src.keyword_generator import LIFECYCLE_STAGES, generate_keywords
from src.lifecycle_classifier import STAGE_COLORS, STAGE_DESCRIPTIONS, classify_lifecycle
from src.lifecycle_curve_models import classify_product_curve_from_series
from src.trend_analytics import analyze_all_windows
from src.trends_bigquery import fetch_suggested_trends
from src.demo_trends import build_demo_multi_window, demo_related_queries
from src.trends_fetcher import extract_related_terms, fetch_multi_window_curves, fetch_related_queries

load_dotenv()

app = FastAPI(title="TrendClimber API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class AnalyzeRequest(BaseModel):
    title: str = Field(min_length=1)
    description: str = Field(min_length=1)
    geo: str = "ES"
    extraKeywords: list[str] = Field(default_factory=list)


class BrandProfileRequest(BaseModel):
    brandName: str = Field(min_length=1)
    sector: str = Field(min_length=1)
    targetAudience: str = Field(min_length=1)
    brandStrategy: str = ""
    brandTone: str | None = None
    primaryChannels: list[str] = Field(default_factory=list)
    objective: str | None = None
    constraints: str = ""


class BrandStrategyRequest(BaseModel):
    brand: BrandProfileRequest
    trendTitle: str = Field(min_length=1)
    geo: str = "ES"
    analyze: dict


def _merge_keywords(
    ai_keywords: list[str],
    extra: list[str],
    related: list[str] | None = None,
    max_count: int = 5,
) -> list[str]:
    seen: set[str] = set()
    merged: list[str] = []
    for kw in list(extra) + list(related or []) + list(ai_keywords):
        normalized = kw.strip()
        if not normalized:
            continue
        key = normalized.lower()
        if key in seen:
            continue
        seen.add(key)
        merged.append(normalized)
        if len(merged) >= max_count:
            break
    return merged


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/stages")
def stages():
    return {
        "stages": LIFECYCLE_STAGES,
        "descriptions": STAGE_DESCRIPTIONS,
        "colors": STAGE_COLORS,
    }


@app.get("/trends/suggested")
def suggested_trends(geo: str = "", limit: int = 12):
    try:
        trends = fetch_suggested_trends(geo=geo, limit=limit)
        return {"trends": trends, "geo": geo, "count": len(trends)}
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al obtener trends sugeridas: {e}") from e


@app.post("/analyze")
def analyze(req: AnalyzeRequest):
    try:
        keywords, reasoning = generate_keywords(req.title, req.description, geo=req.geo)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al generar keywords: {e}") from e

    manual = [k.strip() for k in req.extraKeywords if k.strip()]
    seed = manual[0] if manual else keywords[0]

    keywords = _merge_keywords(keywords, manual, [])
    if manual:
        reasoning = (
            f"{reasoning} Keywords manuales incluidas: {', '.join(manual)}."
        )
    if not keywords:
        raise HTTPException(status_code=400, detail="Se requiere al menos una keyword.")

    demo_mode = False
    try:
        timeline, classify_data, data_until, series_by_window = fetch_multi_window_curves(
            keywords, geo=req.geo
        )
    except ValueError as e:
        if "rate limit" in str(e).lower() or "429" in str(e).lower():
            timeline, classify_data, data_until, series_by_window = build_demo_multi_window(
                keywords, geo=req.geo
            )
            demo_mode = True
            reasoning = (
                f"{reasoning} Modo demo: Google Trends no disponible — curva sintética basada en el patrón viral."
            )
        else:
            raise HTTPException(status_code=502, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e)) from e

    related_terms: list[str] = []
    related_raw: dict[str, list] = {"top": [], "rising": []}
    if demo_mode:
        related_raw = demo_related_queries(seed)
        related_terms = extract_related_terms(related_raw)
    else:
        try:
            related_raw = fetch_related_queries(seed, geo=req.geo)
            related_terms = extract_related_terms(related_raw)
            if related_terms:
                reasoning = (
                    f"{reasoning} Related queries (Trends) para «{seed}»: "
                    f"{', '.join(related_terms)}."
                )
        except Exception as e:
            reasoning = f"{reasoning} Related queries no disponibles: {e}"

    try:
        result = classify_lifecycle(classify_data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al clasificar: {e}") from e

    try:
        analytics, forecast = analyze_all_windows(
            series_by_window,
            trend_context={
                "title": req.title,
                "description": req.description,
                "keywords": keywords,
                "stage": result.stage,
                "metrics": result.metrics,
                "relatedQueries": related_raw,
                "geo": req.geo,
            },
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error en analytics: {e}") from e

    curve_series = series_by_window.get("year")
    if curve_series is None:
        curve_series = series_by_window.get("days30")
    product_curve = classify_product_curve_from_series(
        curve_series,
        stage=result.stage,
        metrics=result.metrics,
    )

    return {
        "keywords": keywords,
        "reasoning": reasoning,
        "relatedQueries": related_raw,
        "stage": result.stage,
        "confidence": result.confidence,
        "description": result.description,
        "color": STAGE_COLORS[result.stage],
        "metrics": result.metrics,
        "stageScores": result.stage_scores,
        "timeline": timeline,
        "dataUntil": data_until,
        "analytics": analytics,
        "forecast": forecast,
        "productCurveType": product_curve["curveType"],
        "productCurveModel": product_curve["modelName"],
        "productCurveFitError": product_curve["fitError"],
        "productCurveSource": product_curve["source"],
        "demoMode": demo_mode,
    }


@app.post("/brand-strategy")
def brand_strategy(req: BrandStrategyRequest):
    trend = summarize_analyze_response(
        req.analyze,
        title=req.trendTitle,
        geo=req.geo,
    )
    brand = req.brand.model_dump(exclude_none=True)

    try:
        return generate_brand_strategy(brand, trend)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error en estrategia de marca: {e}") from e
