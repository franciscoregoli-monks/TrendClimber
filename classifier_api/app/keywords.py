"""Genera keywords de búsqueda con Gemini a partir de un trend."""

from __future__ import annotations

import json
import os
import re
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()
load_dotenv(Path(__file__).resolve().parents[2] / ".env")

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

GEO_LABELS = {
    "ES": "España",
    "AR": "Argentina",
    "MX": "México",
    "": "Global",
}


def _get_model():
    import google.generativeai as genai

    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError(
            "GOOGLE_API_KEY no configurada. Configura la clave de Google AI Studio."
        )
    genai.configure(api_key=api_key)
    return genai.GenerativeModel("gemini-pro-latest")


def _parse_json_response(text: str) -> dict:
    text = text.strip()
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        raise ValueError(f"No se pudo parsear la respuesta del LLM: {text[:200]}")
    return json.loads(match.group())


def generate_keywords(title: str, description: str = "", geo: str = "ES") -> tuple[list[str], str]:
    """Devuelve (keywords, reasoning). Requiere GOOGLE_API_KEY."""
    if not os.getenv("GOOGLE_API_KEY"):
        raise ValueError(
            "GOOGLE_API_KEY no configurada. Configura la clave de Google AI Studio."
        )

    geo_label = GEO_LABELS.get(geo, geo or "Global")
    description = description.strip() or title
    model = _get_model()
    prompt = KEYWORD_PROMPT.format(
        title=title.strip(),
        description=description,
        geo_label=geo_label,
    )
    response = model.generate_content(prompt)
    parsed = _parse_json_response(response.text or "")

    keywords = [k.strip() for k in parsed.get("keywords", []) if str(k).strip()]
    if len(keywords) < 2:
        raise ValueError("El LLM no devolvió suficientes keywords de búsqueda.")

    keywords = keywords[:5]
    reasoning = str(parsed.get("reasoning", "")).strip()
    return keywords, reasoning
