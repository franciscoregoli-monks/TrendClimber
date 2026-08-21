import type { AnalyzeResponse, CurveKey, TimelinePoint, WindowForecast } from "./types";

const TIMELINE_VALUE_KEY: Record<CurveKey, keyof TimelinePoint> = {
  year: "year",
  days30: "days30",
  days7: "days7",
};

/** Build chart series from unified timeline API field. */
export function timelineToSeries(
  timeline: TimelinePoint[],
  windowKey: CurveKey,
): { date: string; value: number }[] {
  const field = TIMELINE_VALUE_KEY[windowKey];
  return timeline
    .filter((point) => point[field] != null)
    .map((point) => ({
      date: point.date,
      value: point[field] as number,
    }));
}

export function forecastVisibleOnTab(windowKey: CurveKey): boolean {
  return windowKey === "days7" || windowKey === "days30" || windowKey === "year";
}

export type ChartRow = {
  date: string;
  value?: number | null;
  forecast?: number | null;
  lower?: number | null;
  upper?: number | null;
  isFuture?: boolean;
};

export function buildChartData(
  series: { date: string; value: number }[],
  forecast: WindowForecast | null | undefined,
  dataUntil: string,
  showForecast: boolean,
): ChartRow[] {
  const map = new Map<string, ChartRow>();

  series.forEach((point) => {
    map.set(point.date, {
      date: point.date,
      value: point.value,
      forecast: null,
      lower: null,
      upper: null,
      isFuture: false,
    });
  });

  const lastHistorical =
    series.find((point) => point.date === dataUntil) ?? series[series.length - 1];

  if (showForecast && forecast) {
    forecast.timeline.forEach((point) => {
      if (!point.isFuture) return;
      if (point.date <= dataUntil) return;
      if (point.date < forecast.forecastFrom) return;

      map.set(point.date, {
        date: point.date,
        value: null,
        forecast: point.forecast,
        lower: point.lower,
        upper: point.upper,
        isFuture: true,
      });
    });

    if (lastHistorical) {
      const anchor = map.get(lastHistorical.date);
      if (anchor) {
        map.set(lastHistorical.date, {
          ...anchor,
          forecast: lastHistorical.value,
          lower: lastHistorical.value,
          upper: lastHistorical.value,
        });
      }
    }
  }

  return Array.from(map.values()).sort((a, b) => a.date.localeCompare(b.date));
}
