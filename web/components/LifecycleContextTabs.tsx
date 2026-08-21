"use client";

import { useMemo } from "react";

import { STAGE_ENGLISH } from "@/lib/labels";
import type { AnalyzeResponse } from "@/lib/types";

interface LifecycleContextTabsProps {
  result: AnalyzeResponse;
}

export function LifecycleContextTabs({ result }: LifecycleContextTabsProps) {
  const sortedScores = useMemo(
    () =>
      Object.entries(result.stageScores)
        .sort(([, a], [, b]) => b - a)
        .map(([stage, score]) => ({
          stage,
          score,
          label: STAGE_ENGLISH[stage as keyof typeof STAGE_ENGLISH] ?? stage,
          isWinner: stage === result.stage,
        })),
    [result.stageScores, result.stage],
  );

  return (
    <div className="hack-card">
      <div>
        <p className="hack-eyebrow mb-1">Confianza por estadio</p>
        <h3 className="text-lg font-medium tracking-[-0.02em] text-[var(--hack-text)]">
          Desglose del lifecycle
        </h3>
        <p className="mt-2 text-sm text-[var(--hack-text-muted)]">
          Qué tan bien encajó cada estadio con la señal de búsqueda a 30 días.
        </p>
      </div>

      <div className="mt-6 space-y-4">
        {sortedScores.map(({ stage, score, label, isWinner }) => (
          <div key={stage}>
            <div className="mb-2 flex justify-between text-sm">
              <span
                className="font-medium"
                style={{
                  color: isWinner ? "#4f24ee" : "var(--hack-text-secondary)",
                }}
              >
                {label}
                {isWinner && " · detectado"}
              </span>
              <span className="text-[var(--hack-text-muted)]">{score.toFixed(3)}</span>
            </div>
            <div className="hack-progress-track">
              <div
                className="hack-progress-fill"
                style={{
                  width: `${Math.min(score * 100, 100)}%`,
                  opacity: isWinner ? 1 : 0.65,
                }}
              />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
