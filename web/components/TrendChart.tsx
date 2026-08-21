"use client";

import { useMemo } from "react";

import {
  Area,
  CartesianGrid,
  ComposedChart,
  Line,
  ReferenceArea,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { buildChartData, forecastVisibleOnTab, timelineToSeries } from "@/lib/chart-data";
import { WINDOW_LABELS } from "@/lib/labels";
import type { AnalyzeResponse, CurveKey, TimelinePoint, WindowForecast } from "@/lib/types";

interface TrendChartProps {
  timeline: TimelinePoint[];
  analytics: AnalyzeResponse["analytics"];
  forecast: WindowForecast | null;
  dataUntil: string;
  active: CurveKey;
  onActiveChange: (key: CurveKey) => void;
}

const CURVE_KEYS: CurveKey[] = ["year", "days30", "days7"];

const CURVE_COLORS: Record<CurveKey, string> = {
  year: "#0071e3",
  days30: "#f97316",
  days7: "#22c55e",
};

const FORECAST_COLORS = {
  prophet: "#2563eb",
  lifecycle_curve: "#7c3aed",
  pytrends: "#0ea5e9",
} as const;

export function TrendChart({
  timeline,
  analytics,
  forecast,
  dataUntil,
  active,
  onActiveChange,
}: TrendChartProps) {
  const windowMeta = WINDOW_LABELS[active];
  const activeColor = CURVE_COLORS[active];
  const windowAnalytics = analytics[active];
  const showForecast = forecastVisibleOnTab(active);
  const forecastColor = forecast
    ? FORECAST_COLORS[forecast.method] ?? FORECAST_COLORS.pytrends
    : FORECAST_COLORS.pytrends;

  const chartData = useMemo(() => {
    const series = timelineToSeries(timeline, active);
    return buildChartData(series, forecast, dataUntil, showForecast);
  }, [timeline, active, forecast, dataUntil, showForecast]);

  const forecastEndDate = showForecast
    ? forecast?.timeline[forecast.timeline.length - 1]?.date
    : undefined;

  if (!windowAnalytics) {
    return (
      <p className="text-sm text-[var(--hack-text-muted)]">
        No analytics available for this time window.
      </p>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <h3 className="text-base font-medium text-[var(--hack-text)]">
          Interés · {windowMeta.short}
        </h3>
        <div
          className="inline-flex rounded-xl border border-black/[0.08] bg-white p-1 shadow-[0_2px_7px_rgba(0,0,0,0.06)]"
          role="tablist"
          aria-label="Time window"
        >
          {CURVE_KEYS.map((key) => {
            const meta = WINDOW_LABELS[key];
            const isActive = active === key;
            return (
              <button
                key={key}
                type="button"
                role="tab"
                aria-selected={isActive}
                onClick={() => onActiveChange(key)}
                className="rounded-[10px] px-4 py-2 text-sm font-medium transition-all"
                style={
                  isActive
                    ? {
                        backgroundColor: CURVE_COLORS[key],
                        color: "#fff",
                        boxShadow: "0 2px 8px rgba(0,0,0,0.12)",
                      }
                    : {
                        backgroundColor: "transparent",
                        color: "var(--hack-text-secondary)",
                      }
                }
              >
                {meta.short}
              </button>
            );
          })}
        </div>
      </div>

      <div className="h-[360px] w-full">
        <ResponsiveContainer width="100%" height="100%">
          <ComposedChart
            key={`${active}-${showForecast ? forecast?.method : "none"}`}
            data={chartData}
            margin={{ top: 12, right: 16, left: 0, bottom: 0 }}
          >
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(0,0,0,0.06)" />
            <XAxis
              dataKey="date"
              tick={{ fill: "#656982", fontSize: 12 }}
              tickFormatter={(v: string) => v.slice(5)}
              axisLine={{ stroke: "rgba(0,0,0,0.08)" }}
              tickLine={false}
            />
            <YAxis
              tick={{ fill: "#656982", fontSize: 12 }}
              axisLine={false}
              tickLine={false}
            />
            <Tooltip
              contentStyle={{
                background: "#fff",
                border: "1px solid rgba(0,0,0,0.1)",
                borderRadius: "12px",
                boxShadow: "0 4px 14px rgba(0,0,0,0.08)",
              }}
              labelStyle={{ color: "#3c3c3e", fontWeight: 500 }}
            />
            {showForecast && forecast && forecastEndDate && (
              <ReferenceArea
                x1={dataUntil}
                x2={forecastEndDate}
                fill={forecastColor}
                fillOpacity={0.06}
                ifOverflow="extendDomain"
              />
            )}
            {showForecast && forecast && (
              <ReferenceLine
                x={dataUntil}
                stroke={forecastColor}
                strokeDasharray="4 4"
                strokeOpacity={0.45}
                label={{
                  value: "Proyección →",
                  position: "insideTopRight",
                  fill: forecastColor,
                  fontSize: 11,
                }}
              />
            )}
            {showForecast && forecast && (
              <>
                <Area
                  type="monotone"
                  dataKey="upper"
                  stroke="none"
                  fill={`${forecastColor}22`}
                  name="Upper band"
                  legendType="none"
                  connectNulls
                  isAnimationActive={false}
                />
                <Area
                  type="monotone"
                  dataKey="lower"
                  stroke="none"
                  fill="#ffffff"
                  name="Lower band"
                  legendType="none"
                  connectNulls
                  isAnimationActive={false}
                />
              </>
            )}
            <Line
              type="monotone"
              dataKey="value"
              stroke={activeColor}
              strokeWidth={2}
              dot={{ r: 3, fill: activeColor, strokeWidth: 0 }}
              activeDot={{ r: 5 }}
              name="Interés real"
              connectNulls={false}
              isAnimationActive={false}
            />
            {showForecast && forecast && (
              <Line
                type="monotone"
                dataKey="forecast"
                stroke={forecastColor}
                strokeWidth={2.5}
                strokeDasharray={undefined}
                dot={false}
                activeDot={{ r: 4, fill: forecastColor }}
                name={
                  forecast.method === "prophet"
                    ? "Proyección (Prophet 7d)"
                    : forecast.method === "lifecycle_curve"
                      ? "Proyección (modelo PLC)"
                      : "Proyección (Google Trends)"
                }
                connectNulls
                isAnimationActive={false}
              />
            )}
          </ComposedChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
