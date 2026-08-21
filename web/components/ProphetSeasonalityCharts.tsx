"use client";

import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import type { ProphetSeasonalityComponent } from "@/lib/types";

interface ProphetSeasonalityChartsProps {
  components: ProphetSeasonalityComponent[];
}

function SeasonalityChart({ component }: { component: ProphetSeasonalityComponent }) {
  const maxAbs = Math.max(...component.points.map((p) => Math.abs(p.value)), 0.01);

  return (
    <div className="rounded-xl border border-black/[0.08] bg-white p-4">
      <p className="text-sm font-medium text-[var(--hack-text)]">{component.title}</p>
      <p className="mt-1 text-xs leading-[18px] text-[var(--hack-text-muted)]">
        {component.description}
      </p>
      <div className="mt-4 h-[200px] w-full">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={component.points} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(0,0,0,0.06)" vertical={false} />
            <XAxis
              dataKey="label"
              tick={{ fill: "#656982", fontSize: 11 }}
              axisLine={{ stroke: "rgba(0,0,0,0.08)" }}
              tickLine={false}
            />
            <YAxis
              tick={{ fill: "#656982", fontSize: 11 }}
              axisLine={false}
              tickLine={false}
              width={40}
            />
            <ReferenceLine y={0} stroke="#94a3b8" strokeDasharray="3 3" />
            <Tooltip
              contentStyle={{
                background: "#fff",
                border: "1px solid rgba(0,0,0,0.1)",
                borderRadius: "12px",
              }}
            />
            <Bar dataKey="value" radius={[4, 4, 0, 0]} maxBarSize={32}>
              {component.points.map((entry) => (
                <Cell
                  key={entry.label}
                  fill={entry.value >= 0 ? "#4f24ee" : "#f97316"}
                  opacity={0.35 + (Math.abs(entry.value) / maxAbs) * 0.65}
                />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
      <p className="mt-2 text-xs text-[var(--hack-text-muted)]">
        Positive bars = above-average seasonal lift · Negative = below-average dip
      </p>
    </div>
  );
}

export function ProphetSeasonalityCharts({ components }: ProphetSeasonalityChartsProps) {
  if (!components.length) {
    return (
      <p className="text-sm text-[var(--hack-text-muted)]">
        Not enough 1-year history for Prophet to detect seasonality patterns.
      </p>
    );
  }

  return (
    <div className="grid gap-4 lg:grid-cols-2">
      {components.map((component) => (
        <SeasonalityChart key={component.type} component={component} />
      ))}
    </div>
  );
}
