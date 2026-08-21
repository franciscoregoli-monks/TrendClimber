"use client";

import { useEffect, useMemo, useState, type ReactNode } from "react";

import type { SuggestedTrend } from "@/lib/types";
import { withFeaturedTrend, FEATURED_TREND } from "@/lib/featured-trends";
import { trendSignalLabel } from "@/lib/labels";

interface TrendSuggestionsProps {
  geo: string;
  onSelect: (trend: SuggestedTrend) => void;
  hidden?: boolean;
  children: ReactNode;
}

type CloudSize = "sm" | "md" | "lg";

function cloudSize(signal?: string | null): CloudSize {
  const value = (signal || "").toLowerCase();
  if (value.includes("rising")) return "lg";
  if (value.includes("top")) return "md";
  return "sm";
}

function CloudButton({
  item,
  index,
  onSelect,
}: {
  item: SuggestedTrend;
  index: number;
  onSelect: (trend: SuggestedTrend) => void;
}) {
  const size = cloudSize(item.trendSignal);
  const signal = (item.trendSignal || "").toLowerCase();

  return (
    <button
      type="button"
      onClick={() => onSelect(item)}
      className={`trend-cloud trend-cloud--${size}${signal.includes("rising") ? " trend-cloud--rising" : ""} pointer-events-auto`}
      style={{
        animationDelay: `${(index % 5) * 0.7}s`,
        ["--cloud-rotate" as string]: `${index % 2 === 0 ? -2 : 2}deg`,
      }}
      title={item.trendDescription ?? item.trendSignal}
    >
      <span className="trend-cloud-label line-clamp-2">{item.trend}</span>
      {item.trendSignal && (
        <span className="trend-cloud-meta">{trendSignalLabel(item.trendSignal)}</span>
      )}
    </button>
  );
}

function CloudColumn({
  trends,
  align,
  onSelect,
  offset = 0,
}: {
  trends: SuggestedTrend[];
  align: "start" | "end";
  onSelect: (trend: SuggestedTrend) => void;
  offset?: number;
}) {
  return (
    <div
      className={`flex flex-col gap-10 py-6 ${align === "end" ? "items-end" : "items-start"}`}
      style={{ paddingTop: offset ? `${offset}px` : undefined }}
    >
      {trends.map((item, index) => (
        <CloudButton
          key={`${item.trend}-${item.country}-${item.loadDate}`}
          item={item}
          index={index + offset}
          onSelect={onSelect}
        />
      ))}
    </div>
  );
}

export function TrendSuggestions({
  geo,
  onSelect,
  hidden = false,
  children,
}: TrendSuggestionsProps) {
  const [trends, setTrends] = useState<SuggestedTrend[]>([FEATURED_TREND]);
  const [loading, setLoading] = useState(true);
  const [fetchError, setFetchError] = useState<string | null>(null);

  useEffect(() => {
    if (hidden) return;

    const controller = new AbortController();

    async function load() {
      setLoading(true);
      setFetchError(null);

      try {
        const params = new URLSearchParams({ limit: "10" });
        if (geo) params.set("geo", geo);

        const res = await fetch(`/api/trends/suggested?${params.toString()}`, {
          signal: controller.signal,
        });
        const data = await res.json();

        if (!res.ok) {
          throw new Error(data.error ?? "No se pudieron cargar sugerencias");
        }

        setTrends(withFeaturedTrend(data.trends ?? []));
      } catch (err) {
        if (controller.signal.aborted) return;
        setTrends(withFeaturedTrend([]));
        setFetchError(err instanceof Error ? err.message : "Error al cargar trends");
      } finally {
        if (!controller.signal.aborted) {
          setLoading(false);
        }
      }
    }

    load();
    return () => controller.abort();
  }, [geo, hidden]);

  const { leftTrends, rightTrends } = useMemo(() => {
    const left: SuggestedTrend[] = [];
    const right: SuggestedTrend[] = [];
    trends.forEach((item, index) => {
      (index % 2 === 0 ? left : right).push(item);
    });
    return { leftTrends: left, rightTrends: right };
  }, [trends]);

  if (hidden) {
    return <>{children}</>;
  }

  const showClouds = trends.length > 0;
  const showLoadingExtras = loading;

  return (
    <>
      {/* Mobile: strip above form */}
      {(showClouds || showLoadingExtras) && (
        <div className="mb-5 flex gap-3 overflow-x-auto pb-2 lg:hidden">
          {(showLoadingExtras ? [FEATURED_TREND, ...Array.from({ length: 3 })] : trends.slice(0, 6)).map(
            (item, i) =>
              showLoadingExtras && i > 0 ? (
                <div
                  key={i}
                  className="trend-cloud trend-cloud--sm trend-cloud--loading h-12 w-28 shrink-0"
                />
              ) : (
                <CloudButton
                  key={`m-${(item as SuggestedTrend).trend}`}
                  item={item as SuggestedTrend}
                  index={i}
                  onSelect={onSelect}
                />
              ),
          )}
        </div>
      )}

      {fetchError && (
        <p className="mb-3 text-center text-xs text-[var(--hack-text-muted)] lg:hidden">
          {fetchError}
        </p>
      )}

      {/* Desktop: form center, clouds in side columns — no overlap */}
      <div className="lg:grid lg:grid-cols-[minmax(0,1fr)_minmax(0,640px)_minmax(0,1fr)] lg:items-start lg:gap-x-10 xl:gap-x-16">
        <div className="hidden lg:block">
          {showLoadingExtras && (
            <div className="flex flex-col items-end gap-10 py-8">
              {Array.from({ length: 2 }).map((_, i) => (
                <div key={i} className="trend-cloud trend-cloud--md trend-cloud--loading h-14 w-32" />
              ))}
            </div>
          )}
          {showClouds && (
            <CloudColumn trends={leftTrends} align="end" onSelect={onSelect} offset={24} />
          )}
        </div>

        <div className="relative z-10 w-full min-w-0 justify-self-center">{children}</div>

        <div className="hidden lg:block">
          {showLoadingExtras && (
            <div className="flex flex-col items-start gap-10 py-12">
              {Array.from({ length: 2 }).map((_, i) => (
                <div key={i} className="trend-cloud trend-cloud--sm trend-cloud--loading h-12 w-28" />
              ))}
            </div>
          )}
          {showClouds && (
            <CloudColumn trends={rightTrends} align="start" onSelect={onSelect} offset={48} />
          )}
        </div>
      </div>
    </>
  );
}
