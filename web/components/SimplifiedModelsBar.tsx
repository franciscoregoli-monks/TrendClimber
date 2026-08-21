"use client";

import {
  FASHION_CYCLE_STAGES,
  PRODUCT_CURVE_TYPES,
  resolveProductCurveType,
  getFashionCycleMarkerPosition,
  getFashionCycleStageMeta,
  mapToFashionCycle,
  type ProductCurveType,
} from "@/lib/lifecycle-map";
import { STAGE_ENGLISH } from "@/lib/labels";
import type { AnalyzeResponse } from "@/lib/types";

const W = 340;
const H = 88;
const PAD = { top: 8, right: 8, bottom: 22, left: 8 };
const IW = W - PAD.left - PAD.right;
const IH = H - PAD.top - PAD.bottom;

function x(t: number) {
  return PAD.left + t * IW;
}
function y(v: number) {
  return PAD.top + (1 - v) * IH;
}

function curveBell(t: number) {
  return Math.exp(-Math.pow((t - 0.5) / 0.22, 2));
}
function curveFad(t: number) {
  return Math.exp(-Math.pow((t - 0.12) / 0.06, 2));
}
function curveFashion(t: number) {
  return Math.exp(-Math.pow((t - 0.45) / 0.18, 2));
}
function curveBasic(t: number) {
  if (t < 0.2) return (t / 0.2) * 0.55;
  if (t < 0.55) return 0.55 + ((t - 0.2) / 0.35) * 0.4;
  if (t < 0.78) return 0.95;
  return 0.95 - ((t - 0.78) / 0.22) * 0.85;
}

const CURVES: Record<ProductCurveType, (t: number) => number> = {
  fad: curveFad,
  fashion: curveFashion,
  basic: curveBasic,
};

function miniPath(fn: (t: number) => number) {
  const pts: string[] = [];
  for (let i = 0; i <= 40; i++) {
    const t = i / 40;
    pts.push(`${i === 0 ? "M" : "L"} ${x(t).toFixed(1)} ${y(fn(t)).toFixed(1)}`);
  }
  return pts.join(" ");
}

export function SimplifiedModelsBar({ result }: { result: AnalyzeResponse }) {
  const fashionStage = mapToFashionCycle(result.stage);
  const fashionMeta = getFashionCycleStageMeta(fashionStage);
  const markerX = getFashionCycleMarkerPosition(result.stage);
  const markerY = curveBell(markerX);
  const productType = resolveProductCurveType(result);
  const productLabel = PRODUCT_CURVE_TYPES.find((p) => p.id === productType)?.label;

  return (
    <div className="grid gap-3 sm:grid-cols-2">
      <div className="rounded-2xl border border-white/60 bg-white/55 p-3 backdrop-blur-xl">
        <p className="text-[11px] font-semibold uppercase tracking-wide text-[var(--hack-text-muted)]">
          Ciclo del trend
        </p>
        <svg viewBox={`0 0 ${W} ${H}`} className="mt-2 w-full">
          {FASHION_CYCLE_STAGES.map((z) => (
            <rect
              key={z.id}
              x={x(z.start)}
              y={PAD.top}
              width={x(z.end) - x(z.start)}
              height={IH}
              fill={z.id === fashionStage ? "#0071e322" : "#00000006"}
            />
          ))}
          <path d={miniPath(curveBell)} fill="none" stroke="#1d1d1f" strokeWidth={2} />
          <circle cx={x(markerX)} cy={y(markerY)} r={4} fill="#0071e3" />
          {FASHION_CYCLE_STAGES.map((zone) => (
            <text
              key={zone.id}
              x={x((zone.start + zone.end) / 2)}
              y={PAD.top + IH + 14}
              textAnchor="middle"
              fontSize={8}
              fontWeight={zone.id === fashionStage ? 700 : 500}
              fill={zone.id === fashionStage ? "#0071e3" : "#94a3b8"}
            >
              {zone.label}
            </text>
          ))}
        </svg>
        <div className="mt-1 flex flex-wrap gap-x-2 gap-y-1">
          {FASHION_CYCLE_STAGES.map((stage) => {
            const active = stage.id === fashionStage;
            return (
              <span
                key={stage.id}
                className="text-[10px]"
                style={{
                  color: active ? "#0071e3" : "var(--hack-text-muted)",
                  fontWeight: active ? 600 : 400,
                }}
              >
                {stage.label}
                {active && (
                  <span className="font-semibold"> · Estás acá</span>
                )}
              </span>
            );
          })}
        </div>
        <p className="mt-1 text-[10px] text-[var(--hack-text-muted)]">
          {STAGE_ENGLISH[result.stage]} → {fashionMeta.label}
        </p>
      </div>

      <div className="rounded-2xl border border-white/60 bg-white/55 p-3 backdrop-blur-xl">
        <p className="text-[11px] font-semibold uppercase tracking-wide text-[var(--hack-text-muted)]">
          Tipo de producto
        </p>
        <p className="mt-0.5 text-sm font-medium text-[var(--hack-text)]">{productLabel}</p>
        <svg viewBox={`0 0 ${W} ${H}`} className="mt-2 w-full">
          {(Object.keys(CURVES) as ProductCurveType[]).map((type) => (
            <path
              key={type}
              d={miniPath(CURVES[type])}
              fill="none"
              stroke={type === productType ? "#0071e3" : "#94a3b8"}
              strokeWidth={type === productType ? 2.5 : 1.2}
              opacity={type === productType ? 1 : 0.45}
            />
          ))}
        </svg>
        <div className="mt-1 flex flex-wrap gap-2">
          {PRODUCT_CURVE_TYPES.map((t) => (
            <span
              key={t.id}
              className="text-[10px]"
              style={{
                color: t.id === productType ? "#0071e3" : "var(--hack-text-muted)",
                fontWeight: t.id === productType ? 600 : 400,
              }}
            >
              {t.label}
            </span>
          ))}
        </div>
        <p className="mt-1 text-[10px] text-[var(--hack-text-muted)]">
          {result.productCurveSource === "curve_fit"
            ? "Clasificado por ajuste a la curva Google Trends (1Y)"
            : "Clasificación estimada por métricas"}
          {result.productCurveFitError != null && (
            <> · RMSE {result.productCurveFitError}</>
          )}
        </p>
      </div>
    </div>
  );
}
