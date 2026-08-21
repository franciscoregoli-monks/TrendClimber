import type { AnalyzeResponse, BrandProfile, BrandStrategyRequest } from "./types";

export const VERDICT_LABELS = {
  join: "Subirte al trend",
  wait: "Esperar",
  niche: "Nicho específico",
  avoid: "Evitar",
} as const;

export const VERDICT_COLORS = {
  join: "#22c55e",
  wait: "#eab308",
  niche: "#0071e3",
  avoid: "#ef4444",
} as const;

export const CHANNEL_OPTIONS = [
  "Instagram",
  "TikTok",
  "LinkedIn",
  "YouTube",
  "X",
] as const;

export function buildBrandStrategyRequest(
  brand: BrandProfile,
  trendTitle: string,
  analyze: AnalyzeResponse,
  geo: string,
): BrandStrategyRequest {
  return {
    brand,
    trendTitle,
    geo,
    analyze,
  };
}
