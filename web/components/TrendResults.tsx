"use client";

import { useEffect, useMemo, useRef, useState } from "react";

import { BrandStrategySection } from "./BrandStrategySection";
import { DeepDiveSection } from "./DeepDiveSection";
import { LifecycleContextTabs } from "./LifecycleContextTabs";
import { ProphetSeasonalityCharts } from "./ProphetSeasonalityCharts";
import { QuickSignals } from "./QuickSignals";
import { SimplifiedModelsBar } from "./SimplifiedModelsBar";
import { TheoreticalModelsPanel } from "./TheoreticalModelsPanel";
import { TrendChart } from "./TrendChart";
import { VerdictHeader } from "./VerdictHeader";
import { LIFECYCLE_MODEL_LABELS } from "@/lib/labels";
import type { AnalyzeResponse, CurveKey } from "@/lib/types";

interface TrendResultsProps {
  result: AnalyzeResponse;
  title: string;
  geo?: string;
}

export function TrendResults({ result, title, geo = "ES" }: TrendResultsProps) {
  const [activeWindow, setActiveWindow] = useState<CurveKey>("days7");
  const resultsRef = useRef<HTMLDivElement>(null);
  const activeLifecycle = result.lifecycleByWindow?.[activeWindow];
  const activeForecast = result.forecastByWindow?.[activeWindow] ?? result.forecast;
  const activeResult = useMemo<AnalyzeResponse>(() => {
    if (!activeLifecycle && activeForecast === result.forecast) return result;
    return {
      ...result,
      ...(activeLifecycle
        ? {
            stage: activeLifecycle.stage,
            confidence: activeLifecycle.confidence,
            description: activeLifecycle.description,
            color: activeLifecycle.color,
            metrics: activeLifecycle.metrics,
            stageScores: activeLifecycle.stageScores,
          }
        : {}),
      forecast: activeForecast,
    };
  }, [activeForecast, activeLifecycle, result]);

  useEffect(() => {
    resultsRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
  }, []);

  function downloadCsv() {
    const headers = ["date", "year", "days30", "days7"];
    const rows = result.timeline.map((row) =>
      headers.map((h) => String(row[h as keyof typeof row] ?? "")).join(","),
    );
    const csv = [headers.join(","), ...rows].join("\n");
    const blob = new Blob([csv], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `trend_${title.replace(/\s+/g, "_").toLowerCase()}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  }

  return (
    <div ref={resultsRef} className="space-y-4">
      {result.demoMode && (
        <div className="rounded-2xl border border-amber-200/80 bg-amber-50/90 px-4 py-3 text-sm text-amber-950">
          Modo demo: no se pudieron obtener datos de Google Trends. Mostramos una curva
          sintética para que puedas probar el flujo completo.
        </div>
      )}
      <SimplifiedModelsBar result={activeResult} />

      <VerdictHeader result={activeResult} activeWindow={activeWindow}>
        <TrendChart
          timeline={result.timeline}
          analytics={result.analytics}
          forecast={activeForecast}
          dataUntil={result.dataUntil}
          active={activeWindow}
          onActiveChange={setActiveWindow}
        />
        <div className="mt-3 space-y-3">
          <QuickSignals activeWindow={activeWindow} analytics={result.analytics} />
          {activeForecast?.method === "prophet" && (
            <p className="text-xs leading-[18px] text-[var(--hack-text-muted)]">
              {activeForecast.label}
              {activeForecast.hasSeasonality && " · estacionalidad detectada"}
            </p>
          )}
          {activeForecast?.method === "lifecycle_curve" && activeForecast.modelName && (
            <p className="text-xs leading-[18px] text-[var(--hack-text-muted)]">
              Modelo:{" "}
              <strong className="text-[var(--hack-text-secondary)]">
                {LIFECYCLE_MODEL_LABELS[activeForecast.modelName]}
              </strong>
              {activeForecast.curveType && <> · curva {activeForecast.curveType}</>}
              {activeForecast.fitError != null && <> · RMSE {activeForecast.fitError}</>}
            </p>
          )}
          {activeForecast?.method === "pytrends" && activeForecast.risingQuery && (
            <p className="text-xs leading-[18px] text-[var(--hack-text-muted)]">
              Proyección ajustada con rising query de Trends:{" "}
              <strong className="text-[var(--hack-text-secondary)]">
                {activeForecast.risingQuery}
              </strong>
            </p>
          )}
          {activeForecast?.method === "prophet" && activeForecast.seasonality.length > 0 && (
            <ProphetSeasonalityCharts components={activeForecast.seasonality} />
          )}
        </div>
      </VerdictHeader>

      <BrandStrategySection
        key={activeWindow}
        result={activeResult}
        trendTitle={title}
        geo={geo}
      />

      <DeepDiveSection
        title="Más detalle"
        description="Scores por estadio, gráficos de modelos y datos en bruto."
        defaultOpen={false}
      >
        <div className="space-y-4">
          <LifecycleContextTabs result={activeResult} />
          <TheoreticalModelsPanel result={activeResult} />

          <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <p className="text-sm text-[var(--hack-text-muted)]">
              {result.timeline.length} rows · until {result.dataUntil}
            </p>
            <button type="button" onClick={downloadCsv} className="hack-btn-secondary">
              Descargar CSV
            </button>
          </div>
        </div>
      </DeepDiveSection>
    </div>
  );
}
