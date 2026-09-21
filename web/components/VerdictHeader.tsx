"use client";

import type { ReactNode } from "react";

import { StageBadge } from "./StageBadge";
import {
  FORECAST_METHOD_LABELS,
  SLOPE_ENGLISH,
} from "@/lib/labels";
import type { AnalyzeResponse } from "@/lib/types";

interface VerdictHeaderProps {
  result: AnalyzeResponse;
  children?: ReactNode;
}

/**
 * The direction is derived from the stage server-side, so the headline cannot
 * contradict the label it sits next to. Only fall back to the fitted slope for
 * responses produced before that field existed.
 */
function headlineDirection(result: AnalyzeResponse) {
  return (
    result.metrics.momentum_direction ??
    (
      result.analytics.days7?.slope ??
      result.analytics.days30?.slope ??
      result.analytics.year?.slope
    )?.direction
  );
}

export function VerdictHeader({ result, children }: VerdictHeaderProps) {
  const slopeDirection = headlineDirection(result);
  const forecastLabel = result.forecast
    ? FORECAST_METHOD_LABELS[result.forecast.method]
    : "—";

  return (
    <div className="rounded-[28px] border border-white/60 bg-white/70 p-5 shadow-[0_8px_32px_rgba(0,0,0,0.06)] backdrop-blur-2xl">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div className="min-w-0 flex-1">
          <StageBadge
            stage={result.stage}
            color={result.color}
            confidence={result.confidence}
            analyzedPoints={result.metrics.days_analyzed}
          />
          <p className="mt-3 text-[15px] leading-[22px] text-[var(--hack-text-secondary)]">
            {result.description}
          </p>
        </div>

        <div className="flex shrink-0 flex-wrap gap-2 sm:max-w-[280px] sm:justify-end">
          <StatPill label="Crecimiento" value={`${result.metrics.growth_ratio}x`} />
          {slopeDirection && (
            <StatPill label="Pendiente" value={SLOPE_ENGLISH[slopeDirection]} />
          )}
          <StatPill label="Proyección" value={forecastLabel} />
        </div>
      </div>

      {children && <div className="mt-5 border-t border-black/[0.06] pt-5">{children}</div>}

      <p className="mt-4 text-xs text-[var(--hack-text-muted)]">
        <span className="font-medium text-[var(--hack-text-secondary)]">Keywords:</span>{" "}
        {result.keywords.join(" · ")}
      </p>
      <p className="mt-2 text-xs leading-[18px] text-[var(--hack-text-muted)]">
        {result.reasoning}
      </p>
    </div>
  );
}

function StatPill({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-xl border border-white/50 bg-white/45 px-3 py-2 text-center backdrop-blur-md">
      <p className="text-[10px] uppercase tracking-wide text-[var(--hack-text-muted)]">
        {label}
      </p>
      <p className="text-sm font-semibold text-[var(--hack-text)]">{value}</p>
    </div>
  );
}
