import axios from 'axios';
import type {
  ApiCountry,
  ApiIndicator,
  CountryOption,
  ForecastResponse,
  IndicatorOption,
  IndicatorPoint,
} from './types';

interface ValidationIssue {
  msg?: string;
}

interface ApiErrorResponse {
  detail?: string | ValidationIssue[];
}

const configuredBaseUrl = import.meta.env.VITE_API_BASE_URL?.replace(/\/$/, '');

const apiClient = axios.create({
  baseURL: configuredBaseUrl || '/api',
  timeout: 20_000,
});

export function isRequestCanceled(error: unknown): boolean {
  return axios.isCancel(error)
    || (axios.isAxiosError(error) && error.code === 'ERR_CANCELED');
}

export function getApiErrorMessage(
  error: unknown,
  fallback = 'Unable to complete the request.',
): string {
  if (!axios.isAxiosError<ApiErrorResponse>(error)) {
    return error instanceof Error ? error.message : fallback;
  }

  const detail = error.response?.data?.detail;
  if (typeof detail === 'string') {
    return detail;
  }

  if (Array.isArray(detail)) {
    const messages = detail.map(item => item.msg).filter(Boolean);
    if (messages.length > 0) {
      return messages.join(' ');
    }
  }

  if (error.code === 'ECONNABORTED') {
    return 'The request timed out. Please try again.';
  }

  return error.message || fallback;
}

export async function fetchCountries(signal?: AbortSignal): Promise<CountryOption[]> {
  const response = await apiClient.get<ApiCountry[]>('/countries', { signal });
  return response.data.map(country => ({
    value: country.id,
    label: country.name,
    iso2Code: country.iso2Code,
  }));
}

export async function fetchIndicators(
  searchOrSignal: string | AbortSignal = '',
  signal?: AbortSignal,
): Promise<IndicatorOption[]> {
  const search = typeof searchOrSignal === 'string' ? searchOrSignal : '';
  const requestSignal = typeof searchOrSignal === 'string' ? signal : searchOrSignal;
  const response = await apiClient.get<ApiIndicator[]>('/indicators', {
    params: { search: search || undefined, limit: 50, offset: 0 },
    signal: requestSignal,
  });
  return response.data.map(indicator => ({
    value: indicator.id,
    label: indicator.name,
  }));
}

export async function fetchComparison(
  countryCodes: string[],
  indicatorCode: string,
  startYear: number,
  endYear: number,
  signal?: AbortSignal,
): Promise<IndicatorPoint[]> {
  const params = new URLSearchParams();
  countryCodes.forEach(country => params.append('countries', country));
  params.set('indicator', indicatorCode);
  params.set('start', String(startYear));
  params.set('end', String(endYear));
  const response = await apiClient.get<IndicatorPoint[]>('/data/compare', { params, signal });
  return response.data;
}

export async function fetchData(
  countryCode: string,
  indicatorCode: string,
  startYear: number,
  endYear: number,
  signal?: AbortSignal,
): Promise<IndicatorPoint[]> {
  const response = await apiClient.get<IndicatorPoint[]>('/data', {
    params: {
      country: countryCode,
      indicator: indicatorCode,
      start: startYear,
      end: endYear,
    },
    signal,
  });
  return response.data;
}

export async function fetchForecast(
  countryCode: string,
  indicatorCode: string,
  startYear: number,
  endYear: number,
  yearsAhead: number,
  signal?: AbortSignal,
): Promise<IndicatorPoint[]> {
  const response = await apiClient.get<IndicatorPoint[]>('/forecast', {
    params: {
      country: countryCode,
      indicator: indicatorCode,
      start: startYear,
      end: endYear,
      years_ahead: yearsAhead,
    },
    signal,
  });
  return response.data;
}

export async function fetchForecastEvaluation(
  countryCode: string,
  indicatorCode: string,
  startYear: number,
  endYear: number,
  yearsAhead: number,
  signal?: AbortSignal,
): Promise<ForecastResponse> {
  const response = await apiClient.get<ForecastResponse>('/forecast/evaluate', {
    params: {
      country: countryCode,
      indicator: indicatorCode,
      start: startYear,
      end: endYear,
      years_ahead: yearsAhead,
    },
    signal,
  });
  return response.data;
}
