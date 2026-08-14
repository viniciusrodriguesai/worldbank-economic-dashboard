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
