from typing import Literal

from pydantic import BaseModel, Field

TipoTrend = Literal["fad", "mode", "classic"]
EstadioTrend = Literal[
    "Naciente",
    "Emergente",
    "Crecimiento",
    "Masiva",
    "Saturada",
    "En declive",
]


class ClassifyRequest(BaseModel):
    trend: str = Field(min_length=1, max_length=120, examples=["quiet luxury"])
    geo: str = Field(default="ES", max_length=8, description="Código de región de Google Trends (ES, AR, MX o vacío = global).")
    description: str = Field(default="", max_length=500)


class ClassifyResponse(BaseModel):
    trend: str
    keywords: list[str]
    tipo: TipoTrend
    estadio: EstadioTrend
    confianza: float
    descripcion_tipo: str
    descripcion_estadio: str
    geo: str
    fuente: str
    metricas: dict
    scores_estadio: dict[str, float]
