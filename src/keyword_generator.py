"""Generate Google Trends search keywords from a trend description using Gemini."""

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

KEYWORD_PROMPT = """Eres un analista de tendencias digitales y marketing cultural.

El usuario describe una tendencia emergente. Tu tarea es generar entre 3 y 5 palabras clave
que la gente buscaría en Google para investigar o participar en esta tendencia.

Título de la tendencia: {title}
Descripción: {description}
País/región de interés: {geo_label}

Reglas:
- Usa términos reales que la gente escribiría en Google (español si geo=ES/AR/MX).
- Incluye variaciones: nombre del fenómeno, hashtags sin #, productos o marcas asociadas.
- Evita términos demasiado genéricos ("moda", "tendencia") o demasiado específicos (frases largas).
- Máximo 5 keywords, mínimo 3.

Responde SOLO con un JSON válido en este formato:
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


def _fallback_keywords(title: str, description: str) -> tuple[list[str], str]:
    """Local keyword derivation when Gemini is unavailable."""
    title = title.strip()
    description = (description or "").strip()
    candidates: list[str] = []

    def add(value: str) -> None:
        value = value.strip()
        if not value or len(value) < 2:
            return
        key = value.lower()
        if any(key == c.lower() for c in candidates):
            return
        candidates.append(value)

    add(title)
    words = title.split()
    if len(words) >= 2:
        add(" ".join(words[:2]))
    if len(words) >= 3:
        add(" ".join(words[:3]))

    for token in re.findall(r"[a-záéíóúüñ0-9]{4,}", description.lower()):
        add(token)

    if not candidates:
        candidates = [title or "tendencia"]

    return candidates[:5], (
        f"Keywords derivadas del título «{title}» (Gemini no disponible)."
    )


def generate_keywords(
    title: str,
    description: str,
    geo: str = "ES",
) -> tuple[list[str], str]:
    """Return (keywords, reasoning) for a given trend."""
    geo_labels = {
        "ES": "España",
        "AR": "Argentina",
        "MX": "México",
        "": "Global",
    }
    geo_label = geo_labels.get(geo, geo or "Global")

    if not os.getenv("GOOGLE_API_KEY"):
        return _fallback_keywords(title, description)

    try:
        model = _get_model()
        prompt = KEYWORD_PROMPT.format(
            title=title,
            description=description,
            geo_label=geo_label,
        )
        response = model.generate_content(prompt)
        parsed = _parse_json_response(response.text)

        keywords = parsed.get("keywords", [])
        if not keywords or len(keywords) < 2:
            return _fallback_keywords(title, description)

        keywords = [k.strip() for k in keywords[:5] if k.strip()]
        reasoning = parsed.get("reasoning", "")
        return keywords, reasoning
    except Exception:
        return _fallback_keywords(title, description)
