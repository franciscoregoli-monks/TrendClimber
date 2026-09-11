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

El usuario describe una tendencia. Debes elegir exactamente {max_keywords} keywords
que la gente buscaría hoy en Google para este fenómeno.

Título de la tendencia: {title}
Descripción: {description}
País/región de interés: {geo_label}
Related queries de Google Trends (prioridad alta, términos reales de búsqueda):
{related_block}

Reglas:
- Devuelve exactamente {max_keywords} keywords.
- La primera keyword DEBE ser el título de la tendencia (o una forma de búsqueda equivalente).
- Completá el resto priorizando related queries reales (rising primero, después top).
- Podés reescribir levemente una related query, pero no inventes términos genéricos.
- Evita palabras sueltas como "moda", "tendencia", "viral", "sobre", "redes".
- Español si geo=ES/AR/MX.

Responde SOLO con un JSON válido:
{{"keywords": ["keyword1", "keyword2", "keyword3"], "reasoning": "breve explicación en 1-2 frases"}}
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


def _add_keyword(bucket: list[str], value: str, *, allow_generic: bool = False) -> None:
    cleaned = re.sub(r"\s+", " ", value.strip())
    if not cleaned or len(cleaned) < 2:
        return
    if not allow_generic and is_generic_keyword(cleaned):
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
    """Pick up to 3 keywords: title, then extras, related queries, then ranked context."""
    selected: list[str] = []
    _add_keyword(selected, title, allow_generic=True)

    for source in (extra or [], related_terms or [], ranked_candidates or []):
        for term in source:
            _add_keyword(selected, term)
            if len(selected) >= max_count:
                return selected[:max_count]

    words = title.strip().split()
    if len(words) >= 2:
        _add_keyword(selected, " ".join(words[:2]))

    for token in re.findall(r"[a-záéíóúüñ0-9]{4,}", (description or "").lower()):
        _add_keyword(selected, token)
        if len(selected) >= max_count:
            break

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

    try:
        model = _get_model()
        prompt = KEYWORD_PROMPT.format(
            title=title,
            description=description,
            geo_label=geo_label,
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
        if len(keywords) < 2:
            return _fallback_keywords(title, description, extra=extra, related_terms=related_terms)
        reasoning = str(parsed.get("reasoning", "")).strip()
        if related_terms:
            reasoning = (
                f"{reasoning} Related queries (Trends) para «{title.strip()}»: "
                f"{', '.join(related_terms)}."
            ).strip()
        return keywords, reasoning
    except Exception:
        return _fallback_keywords(title, description, extra=extra, related_terms=related_terms)
