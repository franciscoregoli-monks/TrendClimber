import type { LifecycleStage } from "./types";

export const LIFECYCLE_STAGES: LifecycleStage[] = [
  "Naciente",
  "Emergente",
  "Crecimiento",
  "Masiva",
  "Saturada",
  "En declive",
];

export const STAGE_COLORS: Record<LifecycleStage, string> = {
  Naciente: "#6366f1",
  Emergente: "#22c55e",
  Crecimiento: "#eab308",
  Masiva: "#f97316",
  Saturada: "#ef4444",
  "En declive": "#94a3b8",
};

export const STAGE_DESCRIPTIONS: Record<LifecycleStage, string> = {
  Naciente:
    "La conversación apenas comienza. Volumen de búsqueda muy bajo; detectarla ahora ofrece ventaja de first-mover.",
  Emergente:
    "La tendencia despierta interés creciente desde una base baja. Momento ideal para explorar y posicionarse con autenticidad.",
  Crecimiento:
    "Adopción acelerada y visibilidad en aumento. Buen momento para activar campañas antes de la saturación.",
  Masiva:
    "Alcanzó pico de relevancia y alta visibilidad mainstream. Participar aún tiene impacto, pero la diferenciación es más difícil.",
  Saturada:
    "Alta exposición pero estancamiento o repetición. El riesgo de parecer forzado aumenta; conviene un ángulo único.",
  "En declive":
    "Pierde tracción y el interés cae. Evitar activaciones genéricas; buscar sub-tendencias o pivotar.",
};

export const GEO_OPTIONS = [
  { value: "ES", label: "España", flag: "🇪🇸" },
  { value: "AR", label: "Argentina", flag: "🇦🇷" },
  { value: "MX", label: "México", flag: "🇲🇽" },
  { value: "", label: "Global", flag: "🌍" },
] as const;
