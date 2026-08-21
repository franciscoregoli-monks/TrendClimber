"use client";

import { MA_SIGNAL_ENGLISH, SLOPE_ENGLISH } from "@/lib/labels";
import type { AnalyzeResponse, CurveKey } from "@/lib/types";

interface QuickSignalsProps {
  activeWindow: CurveKey;
  analytics: AnalyzeResponse["analytics"];
}

export function QuickSignals({ activeWindow, analytics }: QuickSignalsProps) {
  const data = analytics[activeWindow];
  if (!data) return null;

  return (
    <div className="flex flex-wrap gap-2">
      <SignalChip label="Pendiente" value={SLOPE_ENGLISH[data.slope.direction]} />
      <SignalChip label="MM" value={MA_SIGNAL_ENGLISH[data.movingAverage.signal]} />
    </div>
  );
}

function SignalChip({ label, value }: { label: string; value: string }) {
  return (
    <span className="inline-flex items-center gap-1.5 rounded-full border border-white/50 bg-white/40 px-3 py-1 text-xs backdrop-blur-md">
      <span className="text-[var(--hack-text-muted)]">{label}</span>
      <span className="font-medium text-[var(--hack-text)]">{value}</span>
    </span>
  );
}
