import type { AnalyzeResponse, LifecycleStage } from "./types";

export type FashionCycleStage =
  | "introduction"
  | "rise"
  | "peak"
  | "decline"
  | "obsolescence";

export type ProductCurveType = "fad" | "fashion" | "basic";

export const FASHION_CYCLE_STAGES: {
  id: FashionCycleStage;
  label: string;
  start: number;
  end: number;
  color: string;
}[] = [
  { id: "introduction", label: "Intro", start: 0, end: 0.18, color: "#dbeafe" },
  { id: "rise", label: "Subida", start: 0.18, end: 0.42, color: "#bfdbfe" },
  { id: "peak", label: "Pico", start: 0.42, end: 0.58, color: "#93c5fd" },
  { id: "decline", label: "Caída", start: 0.58, end: 0.82, color: "#60a5fa" },
  { id: "obsolescence", label: "Obsolesc.", start: 0.82, end: 1, color: "#3b82f6" },
];

export const PRODUCT_LIFECYCLE_ZONES = [
  { label: "Introducción", start: 0, end: 0.25, color: "#dcfce7" },
  { label: "Crecimiento", start: 0.25, end: 0.5, color: "#bbf7d0" },
  { label: "Madurez", start: 0.5, end: 0.75, color: "#86efac" },
  { label: "Declive", start: 0.75, end: 1, color: "#4ade80" },
] as const;

export const PRODUCT_CURVE_TYPES: {
  id: ProductCurveType;
  label: string;
  description: string;
}[] = [
  {
    id: "fad",
    label: "Fad",
    description: "Pico corto — sube rápido y se desvanece.",
  },
  {
    id: "fashion",
    label: "Moda",
    description: "Campana clásica — pico en crecimiento, cae en madurez.",
  },
  {
    id: "basic",
    label: "Producto básico",
    description: "Subida lenta — meseta larga, declive gradual.",
  },
];

const STAGE_TO_FASHION: Record<LifecycleStage, FashionCycleStage> = {
  Naciente: "introduction",
  Emergente: "rise",
  Crecimiento: "rise",
  Masiva: "peak",
  Saturada: "decline",
  "En declive": "obsolescence",
};

const STAGE_MARKER_POSITION: Record<LifecycleStage, number> = {
  Naciente: 0.08,
  Emergente: 0.28,
  Crecimiento: 0.38,
  Masiva: 0.52,
  Saturada: 0.7,
  "En declive": 0.9,
};

export function mapToFashionCycle(stage: LifecycleStage): FashionCycleStage {
  return STAGE_TO_FASHION[stage];
}

export function getFashionCycleMarkerPosition(stage: LifecycleStage): number {
  return STAGE_MARKER_POSITION[stage];
}

/** Prefer API curve classification from Google Trends; fallback to metrics heuristic. */
export function resolveProductCurveType(result: AnalyzeResponse): ProductCurveType {
  if (result.productCurveType) {
    return result.productCurveType;
  }
  return classifyProductCurveType(result);
}

/** Classify fad / fashion / basic from trend metrics (client fallback). */
export function classifyProductCurveType(
  result: AnalyzeResponse,
): ProductCurveType {
  const { metrics, stage } = result;
  const peak = metrics.peak_position;
  const vol = metrics.volatility;
  const growth = metrics.growth_ratio;
  const avgEarly = metrics.avg_early ?? 0;
  const avgRecent = metrics.avg_recent ?? 0;

  if (growth >= 8 || (avgEarly <= 5 && avgRecent >= 20)) {
    return "fad";
  }
  if (vol >= 25 && growth >= 4) {
    return "fad";
  }
  if (peak >= 0.65 && growth >= 5 && avgEarly <= 10) {
    return "fad";
  }
  if (
    (stage === "Naciente" || stage === "Emergente") &&
    peak < 0.4 &&
    vol > 15
  ) {
    return "fad";
  }

  if (growth >= 4 || vol >= 28) {
    return "fashion";
  }
  if (avgEarly <= 8 && avgRecent >= 25) {
    return "fashion";
  }

  if (
    growth < 1.8 &&
    vol < 18 &&
    peak > 0.25 &&
    peak < 0.72 &&
    (stage === "Saturada" || stage === "En declive")
  ) {
    return "basic";
  }
  if (growth < 1.3 && vol < 12 && peak < 0.55) {
    return "basic";
  }

  return "fashion";
}

export function getFashionCycleStageMeta(stage: FashionCycleStage) {
  return FASHION_CYCLE_STAGES.find((s) => s.id === stage)!;
}
