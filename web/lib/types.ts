export type LifecycleStage =
  | "Naciente"
  | "Emergente"
  | "Crecimiento"
  | "Masiva"
  | "Saturada"
  | "En declive";

export type CurveKey = "year" | "days30" | "days7";

export type MaSignal =
  | "golden_cross"
  | "death_cross"
  | "bullish"
  | "bearish"
  | "neutral";

export type SlopeDirection = "bullish" | "bearish" | "flat";

export interface RelatedQueryItem {
  query: string;
  value: number | string;
}

export interface RelatedQueries {
  top: RelatedQueryItem[];
  rising: RelatedQueryItem[];
}

export interface AnalyzeRequest {
  title: string;
  description: string;
  geo: string;
  extraKeywords?: string[];
}

export interface TimelinePoint {
  date: string;
  year: number | null;
  days30: number | null;
  days7: number | null;
}

export interface SlopeAnalysis {
  value: number;
  pctPerPeriod: number;
  direction: SlopeDirection;
  label: string;
}

export interface MovingAverageAnalysis {
  shortWindow: number;
  longWindow: number;
  signal: MaSignal;
  evolutionStage: string;
  label: string;
  lastShort: number;
  lastLong: number;
  priceVsShort: number;
  priceVsLong: number;
}

export interface MaChartPoint {
  date: string;
  value: number;
}

export interface ForecastPoint {
  date: string;
  actual: number | null;
  forecast: number;
  lower: number;
  upper: number;
  isFuture: boolean;
}

export type ForecastMethod = "prophet" | "lifecycle_curve" | "pytrends";

export type LifecycleModelName = "bass" | "lognormal" | "logistic_decay" | "weibull";
export type ProductCurveType = "fad" | "fashion" | "basic";

export interface AnalogReference {
  name: string;
  keywords: string[];
  similarity: string;
  correlation: number;
  matchStart?: string;
  expectedPostPeak?: string;
}

export interface WindowForecast {
  method: ForecastMethod;
  hasSeasonality: boolean;
  forecastDays: number;
  forecastFrom: string;
  timeline: ForecastPoint[];
  seasonality: ProphetSeasonalityComponent[];
  label: string;
  risingQuery?: string | null;
  curveType?: ProductCurveType;
  modelName?: LifecycleModelName;
  fitError?: number;
}

export interface WindowAnalytics {
  slope: SlopeAnalysis;
  movingAverage: MovingAverageAnalysis;
  maChart: MaChartPoint[];
}

export interface SeasonalityPoint {
  label: string;
  value: number;
}

export interface ProphetSeasonalityComponent {
  type: "weekly" | "yearly" | "daily";
  title: string;
  description: string;
  points: SeasonalityPoint[];
}

export interface ProphetForecast {
  forecastDays: number;
  forecastFrom: string;
  timeline: ForecastPoint[];
  seasonality: ProphetSeasonalityComponent[];
}

export interface AnalyzeResponse {
  keywords: string[];
  reasoning: string;
  relatedQueries?: RelatedQueries;
  stage: LifecycleStage;
  confidence: number;
  description: string;
  color: string;
  dataUntil: string;
  metrics: {
    avg_interest: number;
    avg_recent: number;
    avg_early: number;
    max_interest: number;
    growth_ratio: number;
    slope_recent: number;
    peak_position: number;
    volatility: number;
    current_to_peak?: number;
  peak_drawdown?: number;
    peak_age_points?: number;
    acceleration_now?: number;
    acceleration_week?: number;
    baseline_momentum?: number;
    momentum_7?: number;
    momentum_30?: number;
    persistence?: number;
    days_analyzed: number;
  };
  stageScores: Record<string, number>;
  timeline: TimelinePoint[];
  analytics: Partial<Record<CurveKey, WindowAnalytics>>;
  forecast: WindowForecast | null;
  productCurveType?: ProductCurveType;
  productCurveModel?: LifecycleModelName;
  productCurveFitError?: number | null;
  productCurveSource?: "curve_fit" | "heuristic";
  demoMode?: boolean;
}

export interface ApiError {
  error: string;
}

export interface SuggestedTrendUrl {
  title?: string | null;
  uri?: string | null;
  domain?: string | null;
}

export interface SuggestedTrendMetric {
  name?: string | null;
  description?: string | null;
  value?: string | null;
}

export interface SuggestedTrend {
  trend: string;
  trendDescription: string | null;
  trendSource: string;
  trendSignal: string;
  country: string;
  language: string | null;
  loadDate: string | null;
  ingestedAt: string | null;
  urls: SuggestedTrendUrl[];
  metrics: SuggestedTrendMetric[];
}

export interface SuggestedTrendsResponse {
  trends: SuggestedTrend[];
  geo: string;
  count: number;
}

export type BrandVerdict = "join" | "wait" | "niche" | "avoid";
export type BrandTone = "playful" | "premium" | "expert" | "activist";
export type BrandObjective = "awareness" | "consideration" | "conversion";

export interface BrandProfile {
  brandName: string;
  sector: string;
  targetAudience: string;
  brandStrategy?: string;
  brandTone?: BrandTone;
  primaryChannels?: string[];
  objective?: BrandObjective;
  constraints?: string;
}

export interface BrandStrategyRequest {
  brand: BrandProfile;
  trendTitle: string;
  geo: string;
  analyze: AnalyzeResponse;
}

export interface ResonantAudience {
  segment: string;
  why: string;
}

export interface TrendRecommendations {
  summary: string;
  howToJoin: string[];
  resonantAudiences: ResonantAudience[];
  brandDangers: string[];
  timing: string;
}

export interface BrandStrategyResponse {
  verdict: BrandVerdict;
  headline: string;
  fitScore: number;
  rationale: string;
  recommendations: TrendRecommendations;
  baselineVerdict: BrandVerdict;
  source: "gemini" | "rules";
}
