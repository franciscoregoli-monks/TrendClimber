import type { LifecycleStage, MaSignal, SlopeDirection } from "./types";

/** Etiquetas en español para estadios del lifecycle (claves API en español). */
export const STAGE_ENGLISH: Record<LifecycleStage, string> = {
  Naciente: "Naciente",
  Emergente: "Emergente",
  Crecimiento: "Crecimiento",
  Masiva: "Masiva",
  Saturada: "Saturada",
  "En declive": "En declive",
};

export const SLOPE_ENGLISH: Record<SlopeDirection, string> = {
  bullish: "Alcista",
  bearish: "Bajista",
  flat: "Plano",
};

export const SLOPE_HINT: Record<SlopeDirection, string> = {
  bullish: "El interés sube en esta ventana.",
  bearish: "El interés baja en esta ventana.",
  flat: "El interés se mantiene estable.",
};

export const MA_SIGNAL_ENGLISH: Record<MaSignal, string> = {
  golden_cross: "Cruce dorado",
  death_cross: "Cruce de la muerte",
  bullish: "Alcista",
  bearish: "Bajista",
  neutral: "Lateral",
};

export const MA_SIGNAL_HINT: Record<MaSignal, string> = {
  golden_cross: "Momentum corto acaba de volverse positivo vs largo plazo.",
  death_cross: "Momentum corto acaba de volverse negativo vs largo plazo.",
  bullish: "MA corta por encima de la larga — setup constructivo.",
  bearish: "MA corta por debajo de la larga — setup débil.",
  neutral: "Medias móviles mixtas o convergiendo.",
};

export const WINDOW_LABELS = {
  year: { title: "Últimos 12 meses", short: "1A", hint: "Vista macro de la tendencia." },
  days30: { title: "Últimos 30 días", short: "30D", hint: "Mejor balance para señales de lifecycle." },
  days7: { title: "Últimos 7 días", short: "7D", hint: "Pulso reciente y picos." },
} as const;

export const CHART_LEGEND = [
  { color: "#4f24ee", label: "Interés real", style: "solid" },
  { color: "#2563eb", label: "Forecast Prophet", style: "solid" },
  { color: "#0ea5e9", label: "Forecast MA", style: "dotted" },
  { color: "#2563eb22", label: "Banda de confianza 80%", style: "band" },
] as const;

export const FORECAST_METHOD_LABELS = {
  prophet: "Prophet (7 días)",
  lifecycle_curve: "Ciclo de vida del producto",
  pytrends: "Google Trends",
} as const;

export const LIFECYCLE_MODEL_LABELS = {
  bass: "Difusión Bass",
  lognormal: "Log-Normal",
  logistic_decay: "Logística modificada",
  weibull: "Weibull (Fad)",
} as const;

export const TREND_SIGNAL_LABELS: Record<string, string> = {
  rising: "En alza",
  top: "Top",
  trend: "Tendencia",
  rss: "RSS",
};

export function trendSignalLabel(signal?: string | null): string {
  if (!signal) return "";
  return TREND_SIGNAL_LABELS[signal.toLowerCase()] ?? signal;
}
