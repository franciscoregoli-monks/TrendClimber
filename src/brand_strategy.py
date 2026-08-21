"""Brand strategy advisor — rules baseline + Gemini enrichment."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Literal, TypedDict

from dotenv import load_dotenv

from src.keyword_generator import _get_model, _parse_json_response

load_dotenv()

Verdict = Literal["join", "wait", "niche", "avoid"]
BrandTone = Literal["playful", "premium", "expert", "activist"]
Objective = Literal["awareness", "consideration", "conversion"]

VERDICT_AGGRESSIVENESS: dict[Verdict, int] = {
    "join": 3,
    "niche": 2,
    "wait": 1,
    "avoid": 0,
}

STAGE_BASELINE: dict[str, Verdict] = {
    "Naciente": "join",
    "Emergente": "join",
    "Crecimiento": "join",
    "Masiva": "niche",
    "Saturada": "wait",
    "En declive": "avoid",
}

CONSERVATIVE_SECTOR_KEYWORDS = (
    "finanz",
    "finance",
    "bank",
    "banca",
    "pharma",
    "farmac",
    "salud",
    "health",
    "legal",
    "law",
    "insurance",
    "seguro",
    "medic",
)

STAGE_TO_FASHION = {
    "Naciente": "introduction",
    "Emergente": "rise",
    "Crecimiento": "rise",
    "Masiva": "peak",
    "Saturada": "decline",
    "En declive": "obsolescence",
}

VERDICT_HEADLINES: dict[Verdict, str] = {
    "join": "Buen momento para activarte en esta tendencia.",
    "niche": "Participa con un ángulo muy específico; la visibilidad ya es alta.",
    "wait": "Mejor observar y preparar contenido antes de lanzarte.",
    "avoid": "No conviene una activación genérica en este momento.",
}


class BrandProfile(TypedDict, total=False):
    brandName: str
    sector: str
    targetAudience: str
    brandStrategy: str
    brandTone: BrandTone
    primaryChannels: list[str]
    objective: Objective
    constraints: str


class TrendContext(TypedDict, total=False):
    title: str
    geo: str
    keywords: list[str]
    reasoning: str
    stage: str
    confidence: float
    description: str
    metrics: dict[str, float | int]
    stageScores: dict[str, float]
    analytics: dict[str, Any]
    forecast: dict[str, Any] | None
    fashionCycleStage: str
    productCurveType: str


class ResonantAudience(TypedDict):
    segment: str
    why: str


class TrendRecommendations(TypedDict):
    summary: str
    howToJoin: list[str]
    resonantAudiences: list[ResonantAudience]
    brandDangers: list[str]
    timing: str


class BrandStrategyResult(TypedDict):
    verdict: Verdict
    headline: str
    fitScore: int
    rationale: str
    recommendations: TrendRecommendations
    baselineVerdict: Verdict
    source: Literal["gemini", "rules"]


@dataclass
class _Baseline:
    verdict: Verdict
    fit_score: int
    rationale: str
    risks: list[str]
    opportunities: list[str]


def _classify_product_curve(stage: str, metrics: dict[str, Any]) -> str:
    from src.lifecycle_curve_models import classify_product_curve_type

    return classify_product_curve_type(stage, metrics)


def _downgrade_verdict(verdict: Verdict) -> Verdict:
    order: list[Verdict] = ["join", "niche", "wait", "avoid"]
    idx = order.index(verdict)
    return order[min(idx + 1, len(order) - 1)]


def _is_conservative_sector(sector: str) -> bool:
    normalized = sector.lower().strip()
    return any(kw in normalized for kw in CONSERVATIVE_SECTOR_KEYWORDS)


def _merge_verdict(baseline: Verdict, proposed: Verdict) -> Verdict:
    if VERDICT_AGGRESSIVENESS[proposed] > VERDICT_AGGRESSIVENESS[baseline]:
        return baseline
    return proposed


def _normalize_verdict(value: str) -> Verdict | None:
    normalized = value.strip().lower()
    if normalized in VERDICT_AGGRESSIVENESS:
        return normalized  # type: ignore[return-value]
    return None


def _summarize_forecast(forecast: dict[str, Any] | None) -> dict[str, Any] | None:
    if not forecast:
        return None

    timeline = forecast.get("timeline") or []
    future = [p for p in timeline if p.get("isFuture")]
    last_actual = next((p for p in reversed(timeline) if not p.get("isFuture")), None)
    last_forecast = future[-1] if future else None

    summary: dict[str, Any] = {
        "method": forecast.get("method"),
        "hasSeasonality": forecast.get("hasSeasonality"),
        "forecastDays": forecast.get("forecastDays"),
        "forecastFrom": forecast.get("forecastFrom"),
        "label": forecast.get("label"),
    }
    if last_actual and last_forecast:
        actual_val = last_actual.get("actual") or last_actual.get("value")
        forecast_val = last_forecast.get("forecast")
        if actual_val is not None and forecast_val is not None:
            summary["lastActual"] = actual_val
            summary["forecastEnd"] = forecast_val
            summary["direction"] = (
                "up" if forecast_val > actual_val else "down" if forecast_val < actual_val else "flat"
            )
    return summary


def _summarize_analytics(analytics: dict[str, Any] | None) -> dict[str, Any]:
    if not analytics:
        return {}

    summary: dict[str, Any] = {}
    for window in ("days30", "days7", "year"):
        data = analytics.get(window)
        if not data:
            continue
        slope = data.get("slope") or {}
        ma = data.get("movingAverage") or {}
        summary[window] = {
            "slopeDirection": slope.get("direction"),
            "slopePct": slope.get("pctPerPeriod"),
            "maSignal": ma.get("signal"),
            "evolutionStage": ma.get("evolutionStage"),
        }
    return summary


def summarize_analyze_response(
    analyze: dict[str, Any],
    *,
    title: str = "",
    geo: str = "",
) -> TrendContext:
    """Build a compact trend context from a full /analyze payload (no timeline)."""
    metrics = analyze.get("metrics") or {}
    stage = analyze.get("stage", "")
    forecast_raw = analyze.get("forecast")
    analytics_raw = analyze.get("analytics")

    return TrendContext(
        title=title,
        geo=geo,
        keywords=list(analyze.get("keywords") or []),
        reasoning=str(analyze.get("reasoning") or ""),
        stage=stage,
        confidence=float(analyze.get("confidence") or 0),
        description=str(analyze.get("description") or ""),
        metrics={
            k: metrics[k]
            for k in (
                "growth_ratio",
                "peak_position",
                "volatility",
                "avg_recent",
                "avg_interest",
                "slope_recent",
            )
            if k in metrics
        },
        stageScores=dict(analyze.get("stageScores") or {}),
        analytics=_summarize_analytics(analytics_raw),
        forecast=_summarize_forecast(forecast_raw),
        fashionCycleStage=STAGE_TO_FASHION.get(stage, "rise"),
        productCurveType=str(analyze.get("productCurveType") or _classify_product_curve(stage, metrics)),
    )


def _compute_baseline(brand: BrandProfile, trend: TrendContext) -> _Baseline:
    stage = trend.get("stage", "")
    verdict = STAGE_BASELINE.get(stage, "wait")

    if _is_conservative_sector(brand.get("sector", "")):
        verdict = _downgrade_verdict(verdict)

    metrics = trend.get("metrics") or {}
    analytics = trend.get("analytics") or {}
    slope30 = (analytics.get("days30") or {}).get("slopeDirection")
    forecast = trend.get("forecast") or {}

    risks: list[str] = []
    opportunities: list[str] = []

    if verdict == "join":
        opportunities.append("Ventana favorable para posicionarte antes de la saturación.")
    elif verdict == "niche":
        opportunities.append("Puedes ganar share con un ángulo propio y comunidad específica.")
        risks.append("Alta competencia por atención; el mensaje genérico no destaca.")
    elif verdict == "wait":
        risks.append("Riesgo de parecer oportunista si copias formatos ya masificados.")
    else:
        risks.append("El interés de búsqueda está perdiendo tracción.")

    if slope30 == "bearish":
        verdict = _downgrade_verdict(verdict)
        risks.append("La pendiente reciente es bajista.")

    if forecast.get("direction") == "down":
        verdict = _downgrade_verdict(verdict)
        risks.append("El forecast a 30 días apunta a menor interés.")

    if float(metrics.get("volatility", 0)) > 20:
        risks.append("Alta volatilidad: conviene pruebas pequeñas antes de escalar inversión.")

    fit_score = _fit_score(verdict, trend, brand)
    rationale = _baseline_rationale(verdict, stage, brand, trend)

    return _Baseline(
        verdict=verdict,
        fit_score=fit_score,
        rationale=rationale,
        risks=risks or ["Evalúa coherencia con valores de marca antes de publicar."],
        opportunities=opportunities or ["Monitorea señales y prepara assets reutilizables."],
    )


def _fit_score(verdict: Verdict, trend: TrendContext, brand: BrandProfile) -> int:
    base = {"join": 78, "niche": 62, "wait": 45, "avoid": 28}[verdict]
    confidence = float(trend.get("confidence") or 0.5)
    adjustment = int((confidence - 0.5) * 20)

    channels = brand.get("primaryChannels") or []
    if channels and verdict in ("join", "niche"):
        base += 4

    return max(10, min(95, base + adjustment))


def _baseline_rationale(
    verdict: Verdict,
    stage: str,
    brand: BrandProfile,
    trend: TrendContext,
) -> str:
    name = brand.get("brandName") or "Tu marca"
    audience = brand.get("targetAudience") or "tu audiencia"
    product_type = trend.get("productCurveType", "fashion")
    return (
        f"{name} opera en {brand.get('sector', 'su sector')} frente a una tendencia en "
        f"estadio {stage} (curva tipo {product_type}). Para {audience}, "
        f"el baseline recomienda {verdict.upper()}: {VERDICT_HEADLINES[verdict]}"
    )


def _default_how_to_join(brand: BrandProfile, trend: TrendContext, verdict: Verdict) -> list[str]:
    name = brand.get("brandName") or "Tu marca"
    title = trend.get("title") or (trend.get("keywords") or ["esta tendencia"])[0]
    stage = trend.get("stage", "")
    strategy = brand.get("brandStrategy", "").strip()

    tips: list[str] = []
    if verdict == "join":
        tips.extend(
            [
                f"Conecta {title} con un beneficio real para {brand.get('targetAudience', 'tu audiencia')}, no con el hype.",
                f"Aporta el ángulo propio de {name}: qué aporta tu marca que otros no pueden decir.",
                "Participa con autenticidad antes de que el tema se masifique y pierda originalidad.",
            ]
        )
    elif verdict == "niche":
        tips.extend(
            [
                f"Elige un sub-ángulo de {title} donde {name} tenga credibilidad demostrable.",
                "Habla a una comunidad específica dentro del trend, no a todo el mercado.",
                "Prioriza profundidad y coherencia con tu estrategia de marca sobre volumen.",
            ]
        )
    elif verdict == "wait":
        tips.extend(
            [
                f"Observa cómo evoluciona {title} en estadio {stage} antes de publicar.",
                "Prepara narrativas propias alineadas a tu marca mientras el trend se define.",
                "Entra solo cuando puedas aportar valor diferencial, no cuando ya sea ruido.",
            ]
        )
    else:
        tips.extend(
            [
                f"Evita activaciones genéricas sobre {title}; el interés está decayendo.",
                "Reutiliza aprendizajes del trend en contenido evergreen de tu marca.",
                "Reserva energía creativa para tendencias con mejor encaje y timing.",
            ]
        )

    if strategy:
        snippet = strategy if len(strategy) <= 120 else f"{strategy[:120]}…"
        tips.append(f"Filtra cada idea por tu estrategia declarada: {snippet}")

    return tips


def _default_resonant_audiences(brand: BrandProfile, trend: TrendContext) -> list[ResonantAudience]:
    title = trend.get("title") or (trend.get("keywords") or ["esta tendencia"])[0]
    stage = trend.get("stage", "")
    audiences: list[ResonantAudience] = []

    target = brand.get("targetAudience", "").strip()
    if target:
        audiences.append(
            {
                "segment": target,
                "why": (
                    f"Es tu audiencia core; el encaje depende de cómo vincules {title} "
                    "con sus motivaciones reales, no con el meme del momento."
                ),
            }
        )

    product_type = trend.get("productCurveType", "fashion")
    if product_type == "fad":
        audiences.append(
            {
                "segment": "Early adopters y comunidades de nicho",
                "why": (
                    f"En tendencias tipo fad ({stage}), suelen liderar la conversación "
                    "antes de la masificación."
                ),
            }
        )
    elif product_type == "basic":
        audiences.append(
            {
                "segment": "Consumidores pragmáticos del sector",
                "why": (
                    "Buscan utilidad y confianza más que novedad; responden a ángulos "
                    "educativos o de valor concreto."
                ),
            }
        )
    else:
        audiences.append(
            {
                "segment": "Seguidores de lifestyle y cultura pop del sector",
                "why": (
                    f"En ciclos fashion, {title} funciona como señal de identidad "
                    "y pertenencia grupal."
                ),
            }
        )

    sector = brand.get("sector", "").strip()
    if sector:
        audiences.append(
            {
                "segment": f"Interesados en {sector} que ya siguen conversaciones del rubro",
                "why": "Perciben credibilidad cuando la marca aporta contexto experto, no solo tendencia.",
            }
        )

    return audiences[:4]


def _default_brand_dangers(brand: BrandProfile, trend: TrendContext, baseline: _Baseline) -> list[str]:
    dangers = list(baseline.risks)
    name = brand.get("brandName") or "Tu marca"

    dangers.extend(
        [
            f"Copiar el formato viral de la tendencia sin adaptarlo a la voz de {name}.",
            "Forzar el trend cuando no hay conexión real con tu propuesta de valor.",
            "Parecer oportunista o desconectado de los valores declarados de la marca.",
        ]
    )

    constraints = brand.get("constraints", "").strip()
    if constraints:
        dangers.append(f"Incumplir tus restricciones declaradas: {constraints[:100]}.")

    if _is_conservative_sector(brand.get("sector", "")):
        dangers.append(
            "Subestimar el riesgo reputacional en un sector regulado o de alta sensibilidad."
        )

    # Deduplicate while preserving order
    seen: set[str] = set()
    unique: list[str] = []
    for item in dangers:
        key = item.lower()
        if key in seen:
            continue
        seen.add(key)
        unique.append(item)

    return unique[:6]


def _rule_based_strategy(brand: BrandProfile, trend: TrendContext, baseline: _Baseline) -> BrandStrategyResult:
    stage = trend.get("stage", "")
    title = trend.get("title") or (trend.get("keywords") or ["esta tendencia"])[0]

    return BrandStrategyResult(
        verdict=baseline.verdict,
        headline=VERDICT_HEADLINES[baseline.verdict],
        fitScore=baseline.fit_score,
        rationale=baseline.rationale,
        recommendations={
            "summary": (
                f"Recomendación basada en el estadio {stage} del trend «{title}» y el perfil de "
                f"{brand.get('brandName', 'tu marca')}. Enfócate en encaje auténtico, no en "
                "volumen de publicaciones."
            ),
            "howToJoin": _default_how_to_join(brand, trend, baseline.verdict),
            "resonantAudiences": _default_resonant_audiences(brand, trend),
            "brandDangers": _default_brand_dangers(brand, trend, baseline),
            "timing": _default_timing(baseline.verdict, trend),
        },
        baselineVerdict=baseline.verdict,
        source="rules",
    )


def _default_timing(verdict: Verdict, trend: TrendContext) -> str:
    if verdict == "join":
        return "Actúa en las próximas 2–3 semanas mientras el interés sigue en subida."
    if verdict == "niche":
        return "Lanza 1 experimento en 7 días; escala solo si supera tu benchmark de ER."
    if verdict == "wait":
        return "Monitorea 2 semanas; entra cuando veas señal clara en 30D o forecast."
    return "Prioriza contenido atemporal; evita campañas dedicadas al trend."


STRATEGY_PROMPT = """Eres un estratega de marca senior.

Recibirás:
1) Perfil de marca del cliente (incluye su estrategia de comunicación/negocio)
2) Contexto resumido de una tendencia analizada con TrendClimber (estadio, métricas, forecast)
3) Veredicto baseline calculado por reglas (DEBES respetarlo o ser más conservador, nunca más agresivo)

Tu tarea: recomendar si conviene subirse al trend y dar orientación estratégica general — NO un plan
de campaña, NO presupuesto, NO allocation de medios, NO calendario editorial detallado.

Debes cubrir tres ejes:
1) Cómo subirse al trend de forma auténtica y coherente con la marca
2) Qué audiencias o segmentos resuenan más con el tema (y por qué)
3) Qué peligros debe evitar la marca al participar (reputación, tono, timing, sector)

Reglas:
- verdict debe ser uno de: join, wait, niche, avoid
  · join = conviene activarse ya
  · niche = solo con ángulo muy específico de marca
  · wait = observar y preparar, no lanzar activación genérica ahora
  · avoid = no subirse de forma genérica
- NO puedes ser más agresivo que el baseline (si baseline=wait, no uses join)
- fitScore: entero 0-100 (encaje marca ↔ trend en este estadio)
- howToJoin: mínimo 3 recomendaciones generales (principios, ángulos, enfoque — no ads ni budget)
- resonantAudiences: mínimo 2 segmentos con campo "why" explicativo
- brandDangers: mínimo 3 riesgos concretos para la marca
- Conecta siempre con brandStrategy si está presente
- Responde en español
- Responde SOLO JSON válido:

{{
  "verdict": "join|wait|niche|avoid",
  "headline": "...",
  "fitScore": 72,
  "rationale": "...",
  "recommendations": {{
    "summary": "Párrafo estratégico de síntesis (2-4 frases)",
    "howToJoin": ["...", "...", "..."],
    "resonantAudiences": [
      {{ "segment": "...", "why": "..." }},
      {{ "segment": "...", "why": "..." }}
    ],
    "brandDangers": ["...", "...", "..."],
    "timing": "Ventana de oportunidad en lenguaje claro"
  }}
}}

Perfil de marca:
{brand_json}

Contexto de tendencia:
{trend_json}

Baseline (ancla):
{baseline_json}
"""


def _parse_recommendations(
    parsed: dict[str, Any],
    brand: BrandProfile,
    trend: TrendContext,
    baseline: _Baseline,
) -> TrendRecommendations:
    rec = parsed.get("recommendations") or {}
    fallback = _rule_based_strategy(brand, trend, baseline)["recommendations"]

    how_to_join = [str(x) for x in (rec.get("howToJoin") or []) if str(x).strip()]
    if len(how_to_join) < 3:
        how_to_join = fallback["howToJoin"]

    audiences_raw = rec.get("resonantAudiences") or []
    audiences: list[ResonantAudience] = []
    for item in audiences_raw:
        if not isinstance(item, dict):
            continue
        segment = str(item.get("segment", "")).strip()
        why = str(item.get("why", "")).strip()
        if segment and why:
            audiences.append({"segment": segment, "why": why})
    if len(audiences) < 2:
        audiences = fallback["resonantAudiences"]

    dangers = [str(x) for x in (rec.get("brandDangers") or []) if str(x).strip()]
    if len(dangers) < 3:
        dangers = fallback["brandDangers"]

    summary = str(rec.get("summary") or fallback["summary"]).strip()
    timing = str(rec.get("timing") or fallback["timing"]).strip()

    return TrendRecommendations(
        summary=summary,
        howToJoin=how_to_join,
        resonantAudiences=audiences,
        brandDangers=dangers,
        timing=timing,
    )


def _validate_gemini_payload(
    parsed: dict[str, Any],
    brand: BrandProfile,
    trend: TrendContext,
    baseline: _Baseline,
) -> BrandStrategyResult:
    verdict_raw = parsed.get("verdict", baseline.verdict)
    verdict = _normalize_verdict(str(verdict_raw)) or baseline.verdict
    verdict = _merge_verdict(baseline.verdict, verdict)

    fit_raw = parsed.get("fitScore", baseline.fit_score)
    try:
        fit_score = int(fit_raw)
    except (TypeError, ValueError):
        fit_score = baseline.fit_score
    fit_score = max(10, min(95, fit_score))

    return BrandStrategyResult(
        verdict=verdict,
        headline=str(parsed.get("headline") or VERDICT_HEADLINES[verdict]),
        fitScore=fit_score,
        rationale=str(parsed.get("rationale") or baseline.rationale),
        recommendations=_parse_recommendations(parsed, brand, trend, baseline),
        baselineVerdict=baseline.verdict,
        source="gemini",
    )


def generate_brand_strategy(
    brand: BrandProfile,
    trend: TrendContext,
) -> BrandStrategyResult:
    """
    Generate brand strategy from brand profile + summarized trend context.

    Uses rule-based baseline, then Gemini for enrichment. Falls back to rules-only
    if Gemini is unavailable or returns invalid JSON.
    """
    if not brand.get("brandName", "").strip():
        raise ValueError("brandName es obligatorio.")
    if not brand.get("sector", "").strip():
        raise ValueError("sector es obligatorio.")
    if not brand.get("targetAudience", "").strip():
        raise ValueError("targetAudience es obligatorio.")
    if not trend.get("stage"):
        raise ValueError("El contexto de tendencia debe incluir stage.")

    baseline = _compute_baseline(brand, trend)

    try:
        model = _get_model()
        prompt = STRATEGY_PROMPT.format(
            brand_json=json.dumps(brand, ensure_ascii=False, indent=2),
            trend_json=json.dumps(trend, ensure_ascii=False, indent=2),
            baseline_json=json.dumps(
                {
                    "verdict": baseline.verdict,
                    "fitScore": baseline.fit_score,
                    "rationale": baseline.rationale,
                    "risks": baseline.risks,
                    "opportunities": baseline.opportunities,
                },
                ensure_ascii=False,
                indent=2,
            ),
        )
        response = model.generate_content(prompt)
        parsed = _parse_json_response(response.text)
        return _validate_gemini_payload(parsed, brand, trend, baseline)
    except Exception:
        return _rule_based_strategy(brand, trend, baseline)
