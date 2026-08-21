"use client";

import { useState } from "react";

import { buildBrandStrategyRequest } from "@/lib/brand-strategy";
import type { AnalyzeResponse, BrandProfile, BrandStrategyResponse } from "@/lib/types";

import { BrandProfileForm } from "./BrandProfileForm";
import { BrandStrategyPanel } from "./BrandStrategyPanel";

interface BrandStrategySectionProps {
  result: AnalyzeResponse;
  trendTitle: string;
  geo: string;
}

export function BrandStrategySection({ result, trendTitle, geo }: BrandStrategySectionProps) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [strategy, setStrategy] = useState<BrandStrategyResponse | null>(null);

  async function handleSubmit(brand: BrandProfile) {
    setLoading(true);
    setError(null);

    try {
      const res = await fetch("/api/brand-strategy", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(buildBrandStrategyRequest(brand, trendTitle, result, geo)),
      });

      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.error ?? "Error al generar estrategia");
      }

      setStrategy(data as BrandStrategyResponse);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error desconocido");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="hack-card space-y-5">
      <div>
        <p className="hack-eyebrow mb-1">Estrategia de marca</p>
        <h3 className="text-lg font-medium tracking-[-0.02em] text-[var(--hack-text)]">
          ¿Cómo subirte al trend con tu marca?
        </h3>
        <p className="mt-1 text-sm text-[var(--hack-text-muted)]">
          Estadio detectado: <strong>{result.stage}</strong> — recomendaciones generales sobre cómo
          subirte al trend, qué audiencias resuenan y qué evitar como marca.
        </p>
      </div>

      {!strategy ? (
        <>
          <BrandProfileForm loading={loading} onSubmit={handleSubmit} />
          {error && <p className="text-sm text-red-600">{error}</p>}
        </>
      ) : (
        <>
          <BrandStrategyPanel strategy={strategy} />
          <button
            type="button"
            className="hack-btn-secondary"
            onClick={() => setStrategy(null)}
          >
            Editar perfil de marca
          </button>
        </>
      )}
    </div>
  );
}
