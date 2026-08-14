export interface ApiCountry {
  id: string;
  iso2Code: string;
  name: string;
  region: string;
  capitalCity: string;
}

export interface ApiIndicator {
  id: string;
  name: string;
}

export interface CountryOption {
  value: string;
  label: string;
  iso2Code: string;
}

export interface IndicatorOption {
  value: string;
  label: string;
}

export interface IndicatorPoint {
  country: string;
  indicator: string;
  year: number;
  value: number;
}

export interface ChartPoint {
  year: number;
  indicatorValue: number;
}

export interface ForecastPoint extends IndicatorPoint {
  lower_bound: number;
  upper_bound: number;
}

export interface ForecastMetrics {
  mae: number;
  rmse: number;
  mape: number | null;
  smape: number | null;
}

export interface ModelEvaluation {
  selected_model: string;
  selected_order: [number, number, number] | null;
  validation_points: number;
  model_metrics: ForecastMetrics;
  baseline_model: string;
  baseline_metrics: ForecastMetrics;
  beats_baseline: boolean;
}

export interface ForecastResponse {
  history: IndicatorPoint[];
  forecast: ForecastPoint[];
  evaluation: ModelEvaluation;
  horizon: number;
  missing_years: number[];
  warnings: string[];
}

export interface ChartSeries {
  name: string;
  points: ChartPoint[];
}
