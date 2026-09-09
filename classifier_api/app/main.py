"""FastAPI: clasifica un trend en tipo (fad/mode/classic) y estadio."""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.classifier import (
    STAGE_DESCRIPTIONS,
    TIPO_DESCRIPTIONS,
    classify_lifecycle,
    classify_product_curve_from_series,
    to_tipo,
)
from app.keywords import generate_keywords
from app.schemas import ClassifyRequest, ClassifyResponse
from app.trends import fetch_trend_series

app = FastAPI(
    title="Trend Classifier API",
    version="1.0.0",
    description=(
        "Recibe un trend, genera keywords con un LLM, consulta Google Trends "
        "y clasifica tipo (fad, mode, classic) y estadio del ciclo de vida."
    ),
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/labels")
def labels():
    return {
        "tipo": {
            "fad": TIPO_DESCRIPTIONS["fad"],
            "mode": TIPO_DESCRIPTIONS["mode"],
            "classic": TIPO_DESCRIPTIONS["classic"],
        },
        "estadio": STAGE_DESCRIPTIONS,
    }


@app.post("/classify", response_model=ClassifyResponse)
def classify(req: ClassifyRequest):
    trend = req.trend.strip()
    if not trend:
        raise HTTPException(status_code=400, detail="Se requiere un trend.")

    try:
        keywords, _reasoning = generate_keywords(trend, req.description, geo=req.geo)
    except ValueError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Error al generar keywords con el LLM: {exc}") from exc

    try:
        classify_data, year_series = fetch_trend_series(keywords, geo=req.geo)
    except ValueError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Error al consultar Google Trends: {exc}") from exc

    try:
        lifecycle = classify_lifecycle(classify_data)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    curve = classify_product_curve_from_series(
        year_series,
        stage=lifecycle.stage,
        metrics=lifecycle.metrics,
    )
    tipo = to_tipo(str(curve["curveType"]))

    return ClassifyResponse(
        trend=trend,
        tipo=tipo,
        estadio=lifecycle.stage,
        confianza=lifecycle.confidence,
        descripcion_tipo=TIPO_DESCRIPTIONS[tipo],
        descripcion_estadio=lifecycle.description,
        geo=req.geo,
        fuente=str(curve.get("source", "heuristic")),
        metricas=lifecycle.metrics,
        scores_estadio=lifecycle.stage_scores,
    )
