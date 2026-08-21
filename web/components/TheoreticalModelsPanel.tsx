"use client";

import {
  getFashionCycleStageMeta,
  mapToFashionCycle,
  PRODUCT_CURVE_TYPES,
  resolveProductCurveType,
} from "@/lib/lifecycle-map";
import { STAGE_ENGLISH } from "@/lib/labels";
import type { AnalyzeResponse } from "@/lib/types";

import { FashionCycleChart, ProductTypeChart } from "./LifecycleReferenceCharts";

interface TheoreticalModelsPanelProps {
  result: AnalyzeResponse;
}

export function TheoreticalModelsPanel({ result }: TheoreticalModelsPanelProps) {
  const fashionStage = mapToFashionCycle(result.stage);
  const fashionMeta = getFashionCycleStageMeta(fashionStage);
  const productType = resolveProductCurveType(result);
  const productLabel = PRODUCT_CURVE_TYPES.find((p) => p.id === productType)?.label;

  return (
    <div className="hack-card">
      <div className="mb-6">
        <p className="hack-eyebrow mb-1">Theoretical models</p>
        <h3 className="text-lg font-medium tracking-[-0.02em] text-[var(--hack-text)]">
          Where your trend sits on classic curves
        </h3>
        <p className="mt-2 max-w-3xl text-sm leading-[22px] text-[var(--hack-text-muted)]">
          Compare your detected stage against two reference frameworks.{" "}
          <strong className="text-[var(--hack-text)]">{STAGE_ENGLISH[result.stage]}</strong>{" "}
          maps to <strong>{fashionMeta.label}</strong> on the trend cycle and behaves
          most like a <strong>{productLabel}</strong> product curve.
        </p>
      </div>

      <div className="grid gap-8 lg:grid-cols-2">
        <FashionCycleChart result={result} />
        <ProductTypeChart result={result} />
      </div>

      <div className="mt-6 rounded-2xl border border-white/50 bg-white/40 px-4 py-3 backdrop-blur-md">
        <p className="text-sm font-medium text-[var(--hack-text)]">How to read this</p>
        <ul className="mt-2 space-y-1 text-xs leading-[18px] text-[var(--hack-text-secondary)]">
          <li>
            <strong>Trend Cycle</strong> — popularity over time: Introduction → Rise →
            Peak → Decline → Obsolescence. The marker shows your current phase.
          </li>
          <li>
            <strong>Product Life Cycle</strong> — Fad (short spike), Fashion (bell curve),
            Basic (slow build + long tail). The highlighted curve is our best fit for
            your search data.
          </li>
        </ul>
      </div>
    </div>
  );
}
