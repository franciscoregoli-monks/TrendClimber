import type { LifecycleStage } from "@/lib/types";
import { STAGE_ENGLISH } from "@/lib/labels";

interface StageBadgeProps {
  stage: LifecycleStage;
  color: string;
  confidence: number;
}

export function StageBadge({ stage, color, confidence }: StageBadgeProps) {
  return (
    <div className="flex flex-wrap items-center gap-3">
      <div>
        <p className="text-xs font-medium uppercase tracking-wide text-[var(--hack-text-muted)]">
          Estadio del lifecycle
        </p>
        <div className="mt-2 flex flex-wrap items-center gap-3">
          <span className="hack-stage-badge" style={{ backgroundColor: color }}>
            {STAGE_ENGLISH[stage]}
          </span>
        </div>
      </div>
      <span className="text-sm text-[var(--hack-text-muted)]">
        Confianza{" "}
        <strong className="font-medium text-[var(--hack-text)]">
          {Math.round(confidence * 100)}%
        </strong>
      </span>
    </div>
  );
}
