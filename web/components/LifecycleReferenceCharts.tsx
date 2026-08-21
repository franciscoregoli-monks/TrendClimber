"use client";

import {
  FASHION_CYCLE_STAGES,
  PRODUCT_CURVE_TYPES,
  PRODUCT_LIFECYCLE_ZONES,
  resolveProductCurveType,
  getFashionCycleMarkerPosition,
  getFashionCycleStageMeta,
  mapToFashionCycle,
  type ProductCurveType,
} from "@/lib/lifecycle-map";
import { STAGE_ENGLISH } from "@/lib/labels";
import type { AnalyzeResponse } from "@/lib/types";

const W = 720;
const H = 300;
const PAD = { top: 52, right: 24, bottom: 52, left: 56 };
const IW = W - PAD.left - PAD.right;
const IH = H - PAD.top - PAD.bottom;

function x(t: number) {
  return PAD.left + t * IW;
}

function y(v: number) {
  return PAD.top + (1 - v) * IH;
}

function curveFad(t: number): number {
  return Math.exp(-Math.pow((t - 0.12) / 0.06, 2));
}

function curveFashion(t: number): number {
  return Math.exp(-Math.pow((t - 0.45) / 0.18, 2));
}

function curveBasic(t: number): number {
  if (t < 0.2) return (t / 0.2) * 0.55;
  if (t < 0.55) return 0.55 + ((t - 0.2) / 0.35) * 0.4;
  if (t < 0.78) return 0.95;
  return 0.95 - ((t - 0.78) / 0.22) * 0.85;
}

function curveBell(t: number): number {
  return Math.exp(-Math.pow((t - 0.5) / 0.22, 2));
}

function buildPath(fn: (t: number) => number, steps = 100): string {
  const pts: string[] = [];
  for (let i = 0; i <= steps; i++) {
    const t = i / steps;
    pts.push(`${i === 0 ? "M" : "L"} ${x(t).toFixed(1)} ${y(fn(t)).toFixed(1)}`);
  }
  return pts.join(" ");
}

const CURVE_FNS: Record<ProductCurveType, (t: number) => number> = {
  fad: curveFad,
  fashion: curveFashion,
  basic: curveBasic,
};

function AxisLabels({
  yLabel,
  xLabel,
}: {
  yLabel: string;
  xLabel: string;
}) {
  return (
    <>
      <text
        x={14}
        y={PAD.top + IH / 2}
        textAnchor="middle"
        fontSize={10}
        fontWeight={600}
        fill="#64748b"
        transform={`rotate(-90 14 ${PAD.top + IH / 2})`}
      >
        {yLabel}
      </text>
      <text
        x={PAD.left + IW / 2}
        y={H - 8}
        textAnchor="middle"
        fontSize={10}
        fontWeight={600}
        fill="#64748b"
      >
        {xLabel}
      </text>
    </>
  );
}

export function FashionCycleChart({ result }: { result: AnalyzeResponse }) {
  const fashionStage = mapToFashionCycle(result.stage);
  const fashionMeta = getFashionCycleStageMeta(fashionStage);
  const markerX = getFashionCycleMarkerPosition(result.stage);
  const markerY = curveBell(markerX);

  return (
    <div className="flex h-full flex-col">
      <h4 className="text-center font-serif text-xl font-medium tracking-tight text-[#5c6b4a]">
        The Trend Cycle
      </h4>
      <p className="mt-2 text-center text-xs leading-[18px] text-[var(--hack-text-muted)]">
        Your trend is in <strong className="text-[var(--hack-text)]">{fashionMeta.label}</strong>{" "}
        ({STAGE_ENGLISH[result.stage]}).
      </p>

      <div className="mt-4 flex-1 overflow-x-auto rounded-2xl border border-black/[0.08] bg-[#faf9f7] p-3">
        <svg viewBox={`0 0 ${W} ${H}`} className="w-full min-w-[340px]">
          {FASHION_CYCLE_STAGES.map((zone) => (
            <rect
              key={zone.id}
              x={x(zone.start)}
              y={PAD.top}
              width={x(zone.end) - x(zone.start)}
              height={IH}
              fill={zone.id === fashionStage ? "#fce7f3" : "#fdf2f8"}
              opacity={zone.id === fashionStage ? 1 : 0.6}
            />
          ))}

          {[0.18, 0.42, 0.58, 0.82].map((t) => (
            <line
              key={t}
              x1={x(t)}
              x2={x(t)}
              y1={PAD.top}
              y2={PAD.top + IH}
              stroke="#f9a8d4"
              strokeWidth={1.5}
              opacity={0.8}
            />
          ))}

          <path
            d={buildPath(curveBell)}
            fill="none"
            stroke="#374151"
            strokeWidth={3}
            strokeLinecap="round"
          />

          {FASHION_CYCLE_STAGES.map((zone) => (
            <text
              key={zone.id}
              x={x((zone.start + zone.end) / 2)}
              y={PAD.top + IH + 22}
              textAnchor="middle"
              fontSize={9}
              fontWeight={zone.id === fashionStage ? 700 : 500}
              fill={zone.id === fashionStage ? "#4f24ee" : "#64748b"}
              letterSpacing="0.04em"
            >
              {zone.label.toUpperCase()}
            </text>
          ))}

          <line
            x1={x(markerX)}
            x2={x(markerX)}
            y1={y(markerY)}
            y2={PAD.top + IH}
            stroke="#4f24ee"
            strokeWidth={2}
            strokeDasharray="4 3"
          />
          <circle
            cx={x(markerX)}
            cy={y(markerY)}
            r={8}
            fill="#4f24ee"
            stroke="#fff"
            strokeWidth={2}
          />
          <text
            x={x(markerX)}
            y={y(markerY) - 16}
            textAnchor="middle"
            fontSize={11}
            fontWeight={700}
            fill="#4f24ee"
          >
            Estás acá
          </text>

          <AxisLabels
            yLabel="POPULARITY OF TREND"
            xLabel="YEARS TREND IS ACTIVE"
          />
        </svg>
      </div>

      <p className="mt-3 text-xs leading-[18px] text-[var(--hack-text-secondary)]">
        Classic acceptance bell: brands win by acting before the peak, not after
        obsolescence.
      </p>
    </div>
  );
}

export function ProductTypeChart({ result }: { result: AnalyzeResponse }) {
  const productType = resolveProductCurveType(result);
  const productMeta = PRODUCT_CURVE_TYPES.find((p) => p.id === productType)!;

  return (
    <div className="flex h-full flex-col">
      <h4 className="text-center font-serif text-xl font-medium tracking-tight text-[#166534]">
        Product Life Cycle
      </h4>
      <p className="mt-2 text-center text-xs leading-[18px] text-[var(--hack-text-muted)]">
        Closest match:{" "}
        <strong className="text-[var(--hack-purple)]">{productMeta.label}</strong>.
      </p>

      <div className="mt-4 flex-1 overflow-x-auto rounded-2xl border border-black/[0.08] bg-[#f0fdf4] p-3">
        <svg viewBox={`0 0 ${W} ${H}`} className="w-full min-w-[340px]">
          {PRODUCT_LIFECYCLE_ZONES.map((zone) => (
            <rect
              key={zone.label}
              x={x(zone.start)}
              y={PAD.top}
              width={x(zone.end) - x(zone.start)}
              height={IH}
              fill={zone.color}
              opacity={0.85}
            />
          ))}

          {(Object.keys(CURVE_FNS) as ProductCurveType[]).map((type) => {
            const isActive = type === productType;
            const labelPos =
              type === "fad"
                ? { t: 0.12, dy: -10 }
                : type === "fashion"
                  ? { t: 0.42, dy: -24 }
                  : { t: 0.58, dy: -12 };
            const ly = CURVE_FNS[type](labelPos.t);
            return (
              <g key={type}>
                <path
                  d={buildPath(CURVE_FNS[type])}
                  fill="none"
                  stroke="#ffffff"
                  strokeWidth={isActive ? 4 : 2.5}
                  opacity={isActive ? 1 : 0.55}
                  strokeLinecap="round"
                />
                {isActive && (
                  <path
                    d={buildPath(CURVE_FNS[type])}
                    fill="none"
                    stroke="#166534"
                    strokeWidth={1.5}
                    strokeLinecap="round"
                    opacity={0.5}
                  />
                )}
                <text
                  x={x(labelPos.t)}
                  y={y(ly) + labelPos.dy}
                  fontSize={11}
                  fontWeight={isActive ? 700 : 500}
                  fill={isActive ? "#14532d" : "#166534"}
                  opacity={isActive ? 1 : 0.7}
                  transform={`rotate(-32 ${x(labelPos.t)} ${y(ly) + labelPos.dy})`}
                >
                  {PRODUCT_CURVE_TYPES.find((p) => p.id === type)?.label}
                </text>
              </g>
            );
          })}

          {PRODUCT_LIFECYCLE_ZONES.map((zone) => (
            <text
              key={zone.label}
              x={x((zone.start + zone.end) / 2)}
              y={PAD.top + IH + 22}
              textAnchor="middle"
              fontSize={9}
              fontWeight={600}
              fill="#14532d"
              letterSpacing="0.03em"
            >
              {zone.label.toUpperCase()}
            </text>
          ))}

          <AxisLabels yLabel="SALES" xLabel="TIME" />
        </svg>
      </div>

      <div className="mt-3 grid gap-2 sm:grid-cols-3">
        {PRODUCT_CURVE_TYPES.map((type) => {
          const active = type.id === productType;
          return (
            <div
              key={type.id}
              className="rounded-lg border px-2 py-2 text-center"
              style={{
                borderColor: active ? "#4f24ee44" : "rgba(0,0,0,0.06)",
                background: active ? "#f0ecfe" : "transparent",
              }}
            >
              <p
                className="text-[10px] font-semibold uppercase tracking-wide"
                style={{ color: active ? "#4f24ee" : "var(--hack-text-muted)" }}
              >
                {type.label}
                {active && " ✓"}
              </p>
            </div>
          );
        })}
      </div>
    </div>
  );
}

export function LifecycleReferenceCharts({ result }: { result: AnalyzeResponse }) {
  return (
    <div className="grid gap-8 lg:grid-cols-2">
      <FashionCycleChart result={result} />
      <ProductTypeChart result={result} />
    </div>
  );
}
