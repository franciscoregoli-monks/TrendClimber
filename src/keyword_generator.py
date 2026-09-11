"""Generate Google Trends search keywords from a trend description using Gemini."""

from __future__ import annotations

import json
import os
import re

import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

LIFECYCLE_STAGES = [
    "Naciente",
    "Emergente",
    "Crecimiento",
    "Masiva",
    "Saturada",
    "En declive",
]

MAX_KEYWORDS = 3

GENERIC_TERMS = frozenset(
    {
        "tendencia",
        "trend",
        "viral",
        "sobre",
        "redes",
        "online",
        "google",
        "buscar",
        "busqueda",
        "búsqueda",
        "moda",
        "status",
        "senales",
        "señales",
        "comunidades",
        "acumular",
        "que",
        "qué",
        "como",
        "cómo",
        "para",
        "con",
        "una",
        "unos",
        "unas",
        "del",
        "las",
        "los",
        "the",
        "and",
        "for",
    }
)

KEYWORD_PROMPT = """Eres un analista de tendencias digitales y marketing cultural.

El usuario describe una tendencia. Debes elegir entre 1 y {max_keywords} keywords
que la gente buscaría hoy en Google para este fenómeno.

Título de la tendencia: {title}
Descripción: {description}
País/región de interés: {geo_label}
Keywords manuales del usuario (consérvalas solo si son relevantes):
{manual_block}
Related queries de Google Trends (prioridad alta, términos reales de búsqueda):
{related_block}

Reglas:
- Devuelve como máximo {max_keywords} keywords. No completes el cupo con términos irrelevantes.
- La primera keyword DEBE ser el título de la tendencia (o una forma de búsqueda equivalente).
- Evalúa cada keyword de forma independiente: debe identificar inequívocamente este trend.
- Rechaza fragmentos demasiado amplios que pierdan la persona, producto, evento o fenómeno
  identificador. Ejemplo: para "muerte Jorge Messi", "muerte" no es relevante por sí sola.
- Prioriza keywords manuales relevantes y después related queries reales.
- Podés reescribir levemente una related query, pero no inventes términos genéricos.
- Evita palabras sueltas como "moda", "tendencia", "viral", "sobre", "redes".
- Español si geo=ES/AR/MX.

Responde SOLO con un JSON válido:
{{"keywords": ["keyword1", "keyword2"], "reasoning": "explica brevemente por qué cada término identifica el trend y cuáles descartaste"}}
"""


def _get_model():
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError(
            "GOOGLE_API_KEY no configurada. "
            "Crea un archivo .env con tu clave de Google AI Studio."
        )
    genai.configure(api_key=api_key)
    return genai.GenerativeModel("gemini-pro-latest")


def _parse_json_response(text: str) -> dict:
    text = text.strip()
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        raise ValueError(f"No se pudo parsear la respuesta de Gemini: {text[:200]}")
    return json.loads(match.group())


def _normalize(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip().lower())


def is_generic_keyword(value: str) -> bool:
    tokens = re.findall(r"[a-záéíóúüñ0-9]+", value.lower())
    if not tokens:
        return True
    if len(tokens) == 1 and (tokens[0] in GENERIC_TERMS or len(tokens[0]) < 3):
        return True
    return all(token in GENERIC_TERMS or len(token) < 3 for token in tokens)


def is_contextually_relevant_keyword(value: str, title: str) -> bool:
    """Reject generated fragments that are too broad without the trend context."""
    candidate_tokens = re.findall(r"[a-záéíóúüñ0-9]+", value.lower())
    title_tokens = re.findall(r"[a-záéíóúüñ0-9]+", title.lower())
    if not candidate_tokens:
        return False
    if _normalize(value) == _normalize(title):
        return True
    # For a multi-word trend, a generated single word usually loses the entity
    # or phenomenon that makes the search relevant (e.g. "muerte Jorge Messi" -> "muerte").
    if len(title_tokens) >= 2 and len(candidate_tokens) == 1:
        return False
    return True


def _add_keyword(
    bucket: list[str],
    value: str,
    *,
    title: str = "",
    allow_generic: bool = False,
) -> None:
    cleaned = re.sub(r"\s+", " ", value.strip())
    if not cleaned or len(cleaned) < 2:
        return
    if not allow_generic and is_generic_keyword(cleaned):
        return
    if title and not allow_generic and not is_contextually_relevant_keyword(cleaned, title):
        return
    key = _normalize(cleaned)
    if any(_normalize(existing) == key for existing in bucket):
        return
    bucket.append(cleaned)


def select_analysis_keywords(
    title: str,
    description: str = "",
    extra: list[str] | None = None,
    related_terms: list[str] | None = None,
    ranked_candidates: list[str] | None = None,
    max_count: int = MAX_KEYWORDS,
) -> list[str]:
    """Pick up to 3 relevant keywords; Gemini-ranked candidates outrank raw related terms."""
    selected: list[str] = []
    _add_keyword(selected, title, title=title, allow_generic=True)

    # Explicit user input keeps priority. When Gemini ranked candidates are
    # available, do not refill the list with raw terms the model rejected.
    sources = [extra or []]
    sources.append(ranked_candidates if ranked_candidates is not None else (related_terms or []))
    for source in sources:
        for term in source:
            _add_keyword(selected, term, title=title)
            if len(selected) >= max_count:
                return selected[:max_count]

    if not selected and title.strip():
        selected = [title.strip()]
    return selected[:max_count]


def _fallback_keywords(
    title: str,
    description: str,
    extra: list[str] | None = None,
    related_terms: list[str] | None = None,
) -> tuple[list[str], str]:
    keywords = select_analysis_keywords(
        title,
        description,
        extra=extra,
        related_terms=related_terms,
    )
    related_note = ""
    if related_terms:
        related_note = f" Related queries usadas: {', '.join(related_terms[:4])}."
    return keywords, (
        f"Keywords derivadas del título «{title.strip()}»"
        f"{' y de Google Trends' if related_terms else ''}."
        f"{related_note}"
    )


def generate_keywords(
    title: str,
    description: str,
    geo: str = "ES",
    extra: list[str] | None = None,
    related_terms: list[str] | None = None,
) -> tuple[list[str], str]:
    """Return (keywords, reasoning) for a given trend, capped at 3 terms."""
    geo_labels = {
        "ES": "España",
        "AR": "Argentina",
        "MX": "México",
        "": "Global",
    }
    geo_label = geo_labels.get(geo, geo or "Global")
    extra = [item.strip() for item in (extra or []) if item.strip()]
    related_terms = [item.strip() for item in (related_terms or []) if item.strip()]

    if not os.getenv("GOOGLE_API_KEY"):
        return _fallback_keywords(title, description, extra=extra, related_terms=related_terms)

    related_block = "\n".join(f"- {term}" for term in related_terms) or "- (sin related queries)"
    manual_block = "\n".join(f"- {term}" for term in extra) or "- (sin keywords manuales)"

    try:
        model = _get_model()
        prompt = KEYWORD_PROMPT.format(
            title=title,
            description=description,
            geo_label=geo_label,
            manual_block=manual_block,
            related_block=related_block,
            max_keywords=MAX_KEYWORDS,
        )
        response = model.generate_content(prompt)
        parsed = _parse_json_response(response.text)
        ranked = [str(item).strip() for item in parsed.get("keywords", []) if str(item).strip()]
        keywords = select_analysis_keywords(
            title,
            description,
            extra=extra,
            related_terms=related_terms,
            ranked_candidates=ranked,
        )
        reasoning = str(parsed.get("reasoning", "")).strip()
        if related_terms:
            reasoning = (
                f"{reasoning} Related queries (Trends) para «{title.strip()}»: "
                f"{', '.join(related_terms)}."
            ).strip()
        return keywords, reasoning
    except Exception:
        return _fallback_keywords(title, description, extra=extra, related_terms=related_terms)
