"use client";

import { FormEvent, useState, type ReactNode } from "react";

import { CHANNEL_OPTIONS } from "@/lib/brand-strategy";
import type { BrandObjective, BrandProfile, BrandTone } from "@/lib/types";

interface BrandProfileFormProps {
  loading: boolean;
  onSubmit: (profile: BrandProfile) => void;
}

export function BrandProfileForm({ loading, onSubmit }: BrandProfileFormProps) {
  const [brandName, setBrandName] = useState("");
  const [sector, setSector] = useState("");
  const [targetAudience, setTargetAudience] = useState("");
  const [brandStrategy, setBrandStrategy] = useState("");
  const [brandTone, setBrandTone] = useState<BrandTone | "">("");
  const [objective, setObjective] = useState<BrandObjective | "">("");
  const [constraints, setConstraints] = useState("");
  const [channels, setChannels] = useState<string[]>([]);

  function toggleChannel(name: string) {
    setChannels((prev) =>
      prev.includes(name) ? prev.filter((c) => c !== name) : [...prev, name],
    );
  }

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    onSubmit({
      brandName: brandName.trim(),
      sector: sector.trim(),
      targetAudience: targetAudience.trim(),
      brandStrategy: brandStrategy.trim() || undefined,
      brandTone: brandTone || undefined,
      primaryChannels: channels.length ? channels : undefined,
      objective: objective || undefined,
      constraints: constraints.trim() || undefined,
    });
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div className="grid gap-4 sm:grid-cols-2">
        <Field label="Marca" required>
          <input
            className="hack-input"
            value={brandName}
            onChange={(e) => setBrandName(e.target.value)}
            placeholder="Ej. Luna Studio"
            required
          />
        </Field>
        <Field label="Sector" required>
          <input
            className="hack-input"
            value={sector}
            onChange={(e) => setSector(e.target.value)}
            placeholder="Ej. Moda premium, FMCG, fintech"
            required
          />
        </Field>
      </div>

      <Field label="Audiencia objetivo" required>
        <input
          className="hack-input"
          value={targetAudience}
          onChange={(e) => setTargetAudience(e.target.value)}
          placeholder="Ej. Mujeres 25-40 urbanas"
          required
        />
      </Field>

      <Field label="Estrategia de marca" hint="Posicionamiento, tono, objetivos de negocio">
        <textarea
          className="hack-input min-h-[88px] resize-y"
          value={brandStrategy}
          onChange={(e) => setBrandStrategy(e.target.value)}
          placeholder="Ej. Marca premium accesible, foco en sostenibilidad, queremos awareness sin perder exclusividad..."
        />
      </Field>

      <div className="grid gap-4 sm:grid-cols-2">
        <Field label="Tono de marca">
          <select
            className="hack-input"
            value={brandTone}
            onChange={(e) => setBrandTone(e.target.value as BrandTone | "")}
          >
            <option value="">Sin especificar</option>
            <option value="playful">Playful</option>
            <option value="premium">Premium</option>
            <option value="expert">Expert / educativo</option>
            <option value="activist">Activista / purpose</option>
          </select>
        </Field>
        <Field label="Objetivo de campaña">
          <select
            className="hack-input"
            value={objective}
            onChange={(e) => setObjective(e.target.value as BrandObjective | "")}
          >
            <option value="">Sin especificar</option>
            <option value="awareness">Awareness</option>
            <option value="consideration">Consideración</option>
            <option value="conversion">Conversión</option>
          </select>
        </Field>
      </div>

      <Field label="Canales principales">
        <div className="flex flex-wrap gap-2">
          {CHANNEL_OPTIONS.map((name) => {
            const active = channels.includes(name);
            return (
              <button
                key={name}
                type="button"
                onClick={() => toggleChannel(name)}
                className="rounded-full border px-3 py-1.5 text-xs font-medium transition-colors"
                style={
                  active
                    ? { backgroundColor: "#0071e3", borderColor: "#0071e3", color: "#fff" }
                    : { borderColor: "rgba(0,0,0,0.1)", color: "var(--hack-text-secondary)" }
                }
              >
                {name}
              </button>
            );
          })}
        </div>
      </Field>

      <Field label="Restricciones" hint="Legal, tono prohibido, B2B, etc.">
        <textarea
          className="hack-input min-h-[64px] resize-y"
          value={constraints}
          onChange={(e) => setConstraints(e.target.value)}
          placeholder="Ej. Sin humor meme, solo B2B, evitar claims médicos..."
        />
      </Field>

      <button type="submit" className="hack-btn-primary w-full sm:w-auto" disabled={loading}>
        {loading ? "Generando estrategia…" : "Obtener estrategia para mi marca"}
      </button>
    </form>
  );
}

function Field({
  label,
  hint,
  required,
  children,
}: {
  label: string;
  hint?: string;
  required?: boolean;
  children: ReactNode;
}) {
  return (
    <div>
      <label className="mb-1.5 block text-sm font-medium text-[var(--hack-text)]">
        {label}
        {required && <span className="text-[var(--hack-text-muted)]"> *</span>}
      </label>
      {hint && <p className="mb-2 text-xs text-[var(--hack-text-muted)]">{hint}</p>}
      {children}
    </div>
  );
}
