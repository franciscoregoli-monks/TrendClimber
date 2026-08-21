"use client";

import { FormEvent, KeyboardEvent, useState } from "react";

import { GEO_OPTIONS } from "@/lib/constants";
import { FEATURED_TREND } from "@/lib/featured-trends";
import type { AnalyzeResponse, SuggestedTrend } from "@/lib/types";

import { TrendResults } from "./TrendResults";
import { TrendSuggestions } from "./TrendSuggestions";

const MAX_KEYWORDS = 5;

interface TrendFormProps {
  onResultChange?: (result: AnalyzeResponse | null) => void;
}

export function TrendForm({ onResultChange }: TrendFormProps) {
  const [title, setTitle] = useState(FEATURED_TREND.trend);
  const [description, setDescription] = useState(FEATURED_TREND.trendDescription ?? "");
  const [geo, setGeo] = useState("ES");
  const [keywordInput, setKeywordInput] = useState("");
  const [extraKeywords, setExtraKeywords] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<AnalyzeResponse | null>(null);

  function addKeyword(raw: string) {
    const value = raw.trim();
    if (!value) return;
    if (extraKeywords.length >= MAX_KEYWORDS) return;
    if (extraKeywords.some((k) => k.toLowerCase() === value.toLowerCase())) return;
    setExtraKeywords((prev) => [...prev, value]);
    setKeywordInput("");
  }

  function removeKeyword(keyword: string) {
    setExtraKeywords((prev) => prev.filter((k) => k !== keyword));
  }

  function handleKeywordKeyDown(e: KeyboardEvent<HTMLInputElement>) {
    if (e.key === "Enter") {
      e.preventDefault();
      addKeyword(keywordInput);
    }
  }

  function applySuggestion(item: SuggestedTrend) {
    setTitle(item.trend);
    setDescription(
      item.trendDescription?.trim() ||
        `${item.trendSignal} · Fuente: ${item.trendSource}. Señal detectada en Google Trends.`,
    );
    setError(null);
    setResult(null);
    onResultChange?.(null);
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setResult(null);
    onResultChange?.(null);

    try {
      const controller = new AbortController();
      const timeout = window.setTimeout(() => controller.abort(), 120_000);

      const res = await fetch("/api/analyze", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ title, description, geo, extraKeywords }),
        signal: controller.signal,
      });

      window.clearTimeout(timeout);
      const data = await res.json();

      if (!res.ok) {
        throw new Error(data.error ?? data.detail ?? "Error al analizar la tendencia");
      }

      setResult(data);
      onResultChange?.(data);
    } catch (err) {
      if (err instanceof DOMException && err.name === "AbortError") {
        setError(
          "El análisis tardó demasiado. Google Trends puede estar limitando solicitudes — espera 1 minuto e intenta de nuevo.",
        );
      } else {
        setError(err instanceof Error ? err.message : "Error desconocido");
      }
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="space-y-8">
      <TrendSuggestions geo={geo} onSelect={applySuggestion} hidden={!!result}>
        <form onSubmit={handleSubmit} className="hack-card-form">
          <p className="hack-eyebrow mb-4">Analizar tendencia</p>

        <div className="grid gap-6 sm:grid-cols-2">
          <div>
            <label htmlFor="title" className="hack-label">
              Título de la tendencia
            </label>
            <input
              id="title"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="Ej: farmear aura"
              className="hack-input"
              required
            />
          </div>

          <div>
            <label htmlFor="geo" className="hack-label">
              Región
            </label>
            <select
              id="geo"
              value={geo}
              onChange={(e) => setGeo(e.target.value)}
              className="hack-select"
            >
              {GEO_OPTIONS.map((opt) => (
                <option key={opt.value || "global"} value={opt.value}>
                  {opt.flag} {opt.label}
                </option>
              ))}
            </select>
          </div>
        </div>

        <div className="mt-6">
          <label htmlFor="description" className="hack-label">
            Descripción
          </label>
          <textarea
            id="description"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="Describe el fenómeno, contexto cultural, audiencia..."
            rows={4}
            className="hack-textarea resize-none"
            required
          />
        </div>

        <div className="mt-6">
          <label htmlFor="extraKeywords" className="hack-label">
            Keywords adicionales <span className="font-normal text-[var(--hack-text-muted)]">(opcional)</span>
          </label>
          <p className="mb-3 text-xs leading-[18px] text-[var(--hack-text-muted)]">
            Añade términos de búsqueda manualmente. Se combinan con los de IA (máx. {MAX_KEYWORDS} en total).
          </p>
          <div className="flex gap-2">
            <input
              id="extraKeywords"
              value={keywordInput}
              onChange={(e) => setKeywordInput(e.target.value)}
              onKeyDown={handleKeywordKeyDown}
              placeholder="Ej: quiet luxury aesthetic"
              className="hack-input"
              disabled={extraKeywords.length >= MAX_KEYWORDS}
            />
            <button
              type="button"
              onClick={() => addKeyword(keywordInput)}
              disabled={!keywordInput.trim() || extraKeywords.length >= MAX_KEYWORDS}
              className="hack-btn-secondary shrink-0 whitespace-nowrap"
            >
              Añadir
            </button>
          </div>
          {extraKeywords.length > 0 && (
            <div className="mt-3 flex flex-wrap gap-2">
              {extraKeywords.map((kw) => (
                <span
                  key={kw}
                  className="inline-flex items-center gap-1.5 rounded-full border border-white/50 bg-white/50 py-1 pl-3 pr-1.5 text-xs font-medium text-[var(--hack-text-secondary)] backdrop-blur-md"
                >
                  {kw}
                  <button
                    type="button"
                    onClick={() => removeKeyword(kw)}
                    className="flex h-5 w-5 items-center justify-center rounded-full text-[var(--hack-text-muted)] transition-colors hover:bg-black/5 hover:text-[var(--hack-text)]"
                    aria-label={`Quitar ${kw}`}
                  >
                    ×
                  </button>
                </span>
              ))}
            </div>
          )}
        </div>

        <button type="submit" disabled={loading} className="hack-btn-primary mt-8">
          {loading ? (
            <>
              <span className="hack-spinner" />
              Analizando tendencia...
            </>
          ) : (
            "Analizar tendencia"
          )}
        </button>
        </form>
      </TrendSuggestions>

      {error && <div className="hack-alert-error">{error}</div>}

      {result && <TrendResults result={result} title={title} geo={geo} />}
    </div>
  );
}
