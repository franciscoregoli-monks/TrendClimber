"use client";

import { useState } from "react";

import type { AnalyzeResponse } from "@/lib/types";

import { TrendClimberLogo } from "@/components/TrendClimberLogo";
import { TrendForm } from "@/components/TrendForm";

export function HomeContent() {
  const [hasResults, setHasResults] = useState(false);

  function handleResultChange(result: AnalyzeResponse | null) {
    setHasResults(result !== null);
  }

  return (
    <section className="hack-section min-h-[calc(100vh-58px)]">
      <div className="hack-container">
        <header className="mx-auto max-w-[640px] text-center">
          <div className="mb-5 flex justify-center">
            <TrendClimberLogo showWordmark size="lg" />
          </div>
          <h1 className="sr-only">TrendClimber</h1>
          <p className="hack-subtitle mx-auto">
            Detecta en qué fase está una tendencia antes de que se masifique.
            Ingresa el fenómeno, genera keywords con IA y clasifica su curva
            de búsqueda.
          </p>
        </header>

        <div
          className={`mx-auto mt-12 overflow-visible px-4 ${hasResults ? "max-w-[1160px]" : "max-w-[1180px]"}`}
        >
          <TrendForm onResultChange={handleResultChange} />
        </div>
      </div>
    </section>
  );
}
