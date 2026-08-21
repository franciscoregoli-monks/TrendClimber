"use client";

import { VERDICT_COLORS, VERDICT_LABELS } from "@/lib/brand-strategy";
import type { BrandStrategyResponse, BrandVerdict } from "@/lib/types";

interface BrandStrategyPanelProps {
  strategy: BrandStrategyResponse;
}

export function BrandStrategyPanel({ strategy }: BrandStrategyPanelProps) {
  const { recommendations: rec } = strategy;
  const verdictColor = VERDICT_COLORS[strategy.verdict];

  return (
    <div className="space-y-5">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div className="min-w-0 flex-1">
          <p className="hack-eyebrow mb-2">Recomendación estratégica</p>
          <div className="flex flex-wrap items-start gap-3">
            <VerdictBadge verdict={strategy.verdict} />
            <p className="text-lg font-semibold tracking-[-0.02em] text-[var(--hack-text)]">
              {strategy.headline}
            </p>
          </div>
          <p className="mt-3 text-sm leading-[22px] text-[var(--hack-text-secondary)]">
            {rec.summary || strategy.rationale}
          </p>
          <p className="mt-2 text-xs text-[var(--hack-text-muted)]">
            Encaje marca–trend: {strategy.fitScore}/100
            {strategy.source === "rules" && " · respuesta base (Gemini no disponible)"}
          </p>
        </div>
        <div
          className="rounded-2xl border px-4 py-3 text-center backdrop-blur-md"
          style={{ borderColor: `${verdictColor}44`, backgroundColor: `${verdictColor}11` }}
        >
          <p className="text-[10px] uppercase tracking-wide text-[var(--hack-text-muted)]">
            Fit score
          </p>
          <p className="text-2xl font-bold" style={{ color: verdictColor }}>
            {strategy.fitScore}
          </p>
        </div>
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <InsightBlock
          title="Cómo subirte al trend"
          icon="✓"
          accent="#22c55e"
          items={rec.howToJoin}
        />
        <AudienceBlock audiences={rec.resonantAudiences} />
      </div>

      <InsightBlock
        title="Peligros a evitar como marca"
        icon="!"
        accent="#eab308"
        items={rec.brandDangers}
        variant="warning"
      />

      {rec.timing && (
        <div className="rounded-2xl border border-white/50 bg-white/40 px-4 py-3 backdrop-blur-md">
          <p className="text-[10px] font-semibold uppercase tracking-wide text-[var(--hack-text-muted)]">
            Ventana de oportunidad
          </p>
          <p className="mt-1.5 text-sm leading-[22px] text-[var(--hack-text-secondary)]">
            {rec.timing}
          </p>
        </div>
      )}
    </div>
  );
}

function VerdictBadge({ verdict }: { verdict: BrandVerdict }) {
  const color = VERDICT_COLORS[verdict];
  return (
    <span
      className="inline-flex shrink-0 items-center rounded-full px-3 py-1.5 text-xs font-bold uppercase tracking-wide text-white"
      style={{ backgroundColor: color }}
    >
      {VERDICT_LABELS[verdict]}
    </span>
  );
}

function InsightBlock({
  title,
  icon,
  accent,
  items,
  variant = "default",
}: {
  title: string;
  icon: string;
  accent: string;
  items: string[];
  variant?: "default" | "warning";
}) {
  return (
    <div
      className="rounded-2xl border border-white/50 bg-white/35 p-4 backdrop-blur-md"
      style={variant === "warning" ? { borderColor: `${accent}33` } : undefined}
    >
      <div className="mb-3 flex items-center gap-2">
        <span
          className="flex h-6 w-6 items-center justify-center rounded-full text-xs font-bold text-white"
          style={{ backgroundColor: accent }}
        >
          {icon}
        </span>
        <p className="text-xs font-semibold uppercase tracking-wide text-[var(--hack-text-muted)]">
          {title}
        </p>
      </div>
      <ul className="space-y-2">
        {items.map((item) => (
          <li
            key={item}
            className="flex gap-2 text-sm leading-[20px]"
            style={{
              color: variant === "warning" ? "#92400e" : "var(--hack-text-secondary)",
            }}
          >
            <span style={{ color: accent }}>·</span>
            <span>{item}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}

function AudienceBlock({
  audiences,
}: {
  audiences: BrandStrategyResponse["recommendations"]["resonantAudiences"];
}) {
  return (
    <div className="rounded-2xl border border-white/50 bg-white/35 p-4 backdrop-blur-md">
      <div className="mb-3 flex items-center gap-2">
        <span
          className="flex h-6 w-6 items-center justify-center rounded-full text-xs font-bold text-white"
          style={{ backgroundColor: "#0071e3" }}
        >
          ◎
        </span>
        <p className="text-xs font-semibold uppercase tracking-wide text-[var(--hack-text-muted)]">
          Audiencias que resuenan
        </p>
      </div>
      <div className="space-y-3">
        {audiences.map((audience) => (
          <div key={audience.segment}>
            <p className="text-sm font-medium text-[var(--hack-text)]">{audience.segment}</p>
            <p className="mt-1 text-sm leading-[20px] text-[var(--hack-text-secondary)]">
              {audience.why}
            </p>
          </div>
        ))}
      </div>
    </div>
  );
}
