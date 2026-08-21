"use client";

import { useState, type ReactNode } from "react";

import {
  FORECAST_METHOD_LABELS,
  LIFECYCLE_MODEL_LABELS,
  MA_SIGNAL_ENGLISH,
  MA_SIGNAL_HINT,
  SLOPE_ENGLISH,
  SLOPE_HINT,
  WINDOW_LABELS,
} from "@/lib/labels";
import type { CurveKey, MaSignal, SlopeDirection, WindowForecast } from "@/lib/types";

const SIGNAL_COLORS: Record<MaSignal, string> = {
  golden_cross: "#22c55e",
  death_cross: "#ef4444",
  bullish: "#4f24ee",
  bearish: "#f97316",
  neutral: "#94a3b8",
};

const SLOPE_COLORS: Record<SlopeDirection, string> = {
  bullish: "#22c55e",
  bearish: "#ef4444",
  flat: "#94a3b8",
};

interface InsightRailProps {
  activeWindow: CurveKey;
  slope: {
    value: number;
    pctPerPeriod: number;
    direction: SlopeDirection;
    label: string;
  };
  movingAverage: {
    shortWindow: number;
    longWindow: number;
    signal: MaSignal;
    evolutionStage: string;
    label: string;
    lastShort: number;
    lastLong: number;
    priceVsShort: number;
    priceVsLong: number;
  };
  forecast: WindowForecast | null;
}

function InsightCard({
  eyebrow,
  badge,
  badgeColor,
  title,
  description,
  children,
}: {
  eyebrow: string;
  badge: string;
  badgeColor: string;
  title: string;
  description: string;
  children?: ReactNode;
}) {
  return (
    <div className="rounded-2xl border border-black/[0.08] bg-white p-4 shadow-[0_2px_7px_rgba(0,0,0,0.06)]">
      <p className="text-xs font-medium uppercase tracking-wide text-[var(--hack-text-muted)]">
        {eyebrow}
      </p>
      <div className="mt-2 flex flex-wrap items-center gap-2">
        <span
          className="rounded-full px-2.5 py-0.5 text-xs font-semibold text-white"
          style={{ backgroundColor: badgeColor }}
        >
          {badge}
        </span>
        <span className="text-sm font-medium text-[var(--hack-text)]">{title}</span>
      </div>
      <p className="mt-2 text-xs leading-[18px] text-[var(--hack-text-secondary)]">
        {description}
      </p>
      {children}
    </div>
  );
}

function MetricRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between rounded-lg bg-[var(--hack-tint)] px-3 py-2 text-xs">
      <span className="text-[var(--hack-text-muted)]">{label}</span>
      <span className="font-medium text-[var(--hack-text)]">{value}</span>
    </div>
  );
}

export function InsightRail({
  activeWindow,
  slope,
  movingAverage,
  forecast,
}: InsightRailProps) {
  const [showHelp, setShowHelp] = useState(false);
  const windowLabel = WINDOW_LABELS[activeWindow].short;

  return (
    <div className="space-y-4 lg:sticky lg:top-24">
      <div className="rounded-xl border border-black/[0.08] bg-[var(--hack-tint)] px-4 py-3">
        <p className="text-sm font-medium text-[var(--hack-text)]">
          Insights · {windowLabel}
        </p>
        <button
          type="button"
          onClick={() => setShowHelp((v) => !v)}
          className="mt-1 text-xs font-medium text-[var(--hack-purple)] hover:underline"
        >
          {showHelp ? "Ocultar" : "Cómo leer este gráfico"}
        </button>
        {showHelp && (
          <p className="mt-2 text-xs leading-[18px] text-[var(--hack-text-secondary)]">
            Forecast compartido a 30 días desde Google Trends (interés + consultas relacionadas).
          </p>
        )}
      </div>

      <InsightCard
        eyebrow="Pendiente de la curva"
        badge={SLOPE_ENGLISH[slope.direction]}
        badgeColor={SLOPE_COLORS[slope.direction]}
        title={`${slope.value > 0 ? "+" : ""}${slope.value} por período`}
        description={slope.label || SLOPE_HINT[slope.direction]}
      >
        <div className="mt-3">
          <MetricRow
            label="Cambio relativo"
            value={`${slope.pctPerPeriod > 0 ? "+" : ""}${slope.pctPerPeriod}% / período`}
          />
        </div>
      </InsightCard>

      <InsightCard
        eyebrow="Señal de media móvil"
        badge={MA_SIGNAL_ENGLISH[movingAverage.signal]}
        badgeColor={SIGNAL_COLORS[movingAverage.signal]}
        title={movingAverage.evolutionStage}
        description={movingAverage.label || MA_SIGNAL_HINT[movingAverage.signal]}
      >
        <div className="mt-3 grid gap-2">
          <MetricRow label={`SMA ${movingAverage.shortWindow}`} value={String(movingAverage.lastShort)} />
          <MetricRow label={`SMA ${movingAverage.longWindow}`} value={String(movingAverage.lastLong)} />
        </div>
      </InsightCard>

      {forecast && (
        <div className="rounded-xl border border-black/[0.08] bg-white px-4 py-3">
          <p className="text-xs font-medium uppercase tracking-wide text-[var(--hack-text-muted)]">
            Método de proyección
          </p>
          <p className="mt-2 text-sm text-[var(--hack-text-secondary)]">{forecast.label}</p>
          <div className="mt-3 space-y-2">
            <MetricRow label="Método" value={FORECAST_METHOD_LABELS[forecast.method]} />
            {forecast.modelName && (
              <MetricRow
                label="Modelo PLC"
                value={LIFECYCLE_MODEL_LABELS[forecast.modelName]}
              />
            )}
            {forecast.curveType && (
              <MetricRow label="Tipo de curva" value={forecast.curveType} />
            )}
            <MetricRow label="Horizonte" value={`${forecast.forecastDays} días`} />
            {forecast.risingQuery && (
              <MetricRow label="Consulta en alza" value={forecast.risingQuery} />
            )}
          </div>
        </div>
      )}
    </div>
  );
}
