import type { SuggestedTrend } from "./types";

/** Trend destacada siempre visible en las nubes de sugerencias. */
export const FEATURED_TREND: SuggestedTrend = {
  trend: "farmear aura",
  trendDescription:
    "Tendencia viral en redes sobre acumular estética, status simbólico y señales de identidad en comunidades online.",
  trendSource: "x-trends",
  trendSignal: "rising",
  country: "AR",
  language: "Spanish",
  loadDate: "2026-08-21",
  ingestedAt: null,
  urls: [],
  metrics: [],
};

export function withFeaturedTrend(trends: SuggestedTrend[]): SuggestedTrend[] {
  const rest = trends.filter((t) => t.trend.trim().toLowerCase() !== "farmear aura");
  return [FEATURED_TREND, ...rest];
}
