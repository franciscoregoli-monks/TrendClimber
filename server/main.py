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
    except Exception:
        country = geo or "AR"
        fallback = [
            ("farmear aura", "Identidad, estética y status simbólico en comunidades online."),
            ("agentes de IA autónomos", "Software capaz de planificar y ejecutar tareas con mínima supervisión."),
            ("lujo silencioso", "Consumo premium basado en calidad, diseño sobrio y señales discretas."),
            ("wellness stacking", "Combinación de hábitos de bienestar en rutinas integradas."),
            ("slow travel", "Viajes de mayor duración centrados en experiencias locales."),
            ("social search", "Uso de plataformas sociales como motor de descubrimiento y búsqueda."),
        ][: max(1, min(limit, 6))]
        trends = [
            {
                "trend": trend,
                "trendDescription": description,
                "trendSource": "local-fallback",
                "trendSignal": "rising",
                "country": country,
                "language": "Spanish",
                "loadDate": None,
                "ingestedAt": None,
                "urls": [],
                "metrics": [],
            }
            for trend, description in fallback
        ]
        return {"trends": trends, "geo": geo, "count": len(trends)}


@app.post("/analyze")
def analyze(req: AnalyzeRequest):
    seed = req.title.strip()
    manual = [k.strip() for k in req.extraKeywords if k.strip()]
    related_raw: dict[str, list] = {"top": [], "rising": []}
    related_note = ""

    # 1. Obtener búsquedas relacionadas reales de Google Trends para el término semilla
    try:
        related_raw = fetch_related_queries(seed, geo=req.geo)
        related_terms = extract_related_terms(related_raw)
        if related_terms:
            related_note = (
                f" Related queries (Trends) para «{seed}»: {', '.join(related_terms)}."
            )
    except Exception as e:
        related_terms = []
        related_note = f" Related queries no disponibles: {e}"

    # 2. Generación/selección de las 3 keywords definitivas con Gemini a partir de datos reales
    try:
        keywords, reasoning = generate_keywords(
            req.title,
            req.description,
            geo=req.geo,
            extra=manual,
            related_terms=related_terms,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al generar keywords: {e}") from e

    if related_note and "Related queries" not in reasoning:
        reasoning = f"{reasoning}{related_note}"
    if not keywords:
        raise HTTPException(status_code=400, detail="Se requiere al menos una keyword.")

    # 3. Consulta consolidada a Google Trends para las 3 keywords finales
    demo_mode = False
    try:
        timeline, classify_data, data_until, series_by_window = fetch_multi_window_curves(
            keywords, geo=req.geo
        )
    except Exception as e:
        timeline, classify_data, data_until, series_by_window = build_demo_multi_window(
            keywords, geo=req.geo
        )
        demo_mode = True
        reasoning = (
            f"{reasoning} Modo demo: Google Trends no disponible "
            f"({type(e).__name__}) — curva sintética basada en el patrón viral."
        )
        if not related_raw.get("top") and not related_raw.get("rising"):
            related_raw = demo_related_queries(seed)

    try:
        lifecycle_series = series_by_window.get("year")
        lifecycle_data = (
            lifecycle_series.to_frame(name="total")
            if lifecycle_series is not None and len(lifecycle_series) >= 7
            else classify_data
        )
        result = classify_lifecycle(lifecycle_data)
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
