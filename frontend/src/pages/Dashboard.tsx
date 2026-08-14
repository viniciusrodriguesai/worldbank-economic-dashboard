import { lazy, Suspense, useEffect, useMemo, useRef, useState } from 'react';
import type { ChangeEvent } from 'react';

import {
  fetchComparison,
  fetchCountries,
  fetchForecastEvaluation,
  fetchIndicators,
  getApiErrorMessage,
  isRequestCanceled,
} from '../api';
import CountrySelector from '../components/CountrySelector';
import ExportCSV from '../components/ExportCSV';
import IndicatorSelector from '../components/IndicatorSelector';
import type {
  ChartSeries,
  CountryOption,
  ForecastResponse,
  IndicatorOption,
  IndicatorPoint,
} from '../types';

const LineChart = lazy(() => import('../components/LineChart'));
const MapChart = lazy(() => import('../components/MapChart'));
const currentYear = new Date().getFullYear();
const horizons = [1, 3, 5, 10];

function formatValue(value: number | undefined): string {
  if (value === undefined || !Number.isFinite(value)) return '—';
  return new Intl.NumberFormat('en', { notation: 'compact', maximumFractionDigits: 2 }).format(value);
}

function formatMetric(value: number | null | undefined): string {
  if (value === null || value === undefined || !Number.isFinite(value)) return 'Not available';
  return new Intl.NumberFormat('en', { maximumFractionDigits: 3 }).format(value);
}

export default function Dashboard() {
  const [countries, setCountries] = useState<CountryOption[]>([]);
  const [indicators, setIndicators] = useState<IndicatorOption[]>([]);
  const [selectedCountries, setSelectedCountries] = useState<CountryOption[]>([]);
  const [indicator, setIndicator] = useState<IndicatorOption | null>(null);
  const [indicatorSearch, setIndicatorSearch] = useState('');
  const [range, setRange] = useState({ start: currentYear - 20, end: currentYear });
  const [horizon, setHorizon] = useState(5);
  const [data, setData] = useState<IndicatorPoint[]>([]);
  const [forecast, setForecast] = useState<ForecastResponse | null>(null);
  const [metadataLoading, setMetadataLoading] = useState(true);
  const [dataLoading, setDataLoading] = useState(false);
  const [forecastLoading, setForecastLoading] = useState(false);
  const [message, setMessage] = useState('');
  const forecastControllerRef = useRef<AbortController | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    setMetadataLoading(true);
    Promise.all([fetchCountries(controller.signal), fetchIndicators('', controller.signal)])
      .then(([countryOptions, indicatorOptions]) => {
        setCountries(countryOptions);
        setIndicators(indicatorOptions);
      })
      .catch((error: unknown) => {
        if (!isRequestCanceled(error)) setMessage(getApiErrorMessage(error, 'Failed to load filters.'));
      })
      .finally(() => {
        if (!controller.signal.aborted) setMetadataLoading(false);
      });
    return () => controller.abort();
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    const timer = window.setTimeout(() => {
      fetchIndicators(indicatorSearch, controller.signal)
        .then(setIndicators)
        .catch((error: unknown) => {
          if (!isRequestCanceled(error)) setMessage(getApiErrorMessage(error, 'Indicator search failed.'));
        });
    }, 250);
    return () => {
      window.clearTimeout(timer);
      controller.abort();
    };
  }, [indicatorSearch]);

  useEffect(() => {
    forecastControllerRef.current?.abort();
    setForecast(null);
    if (selectedCountries.length === 0 || !indicator) {
      setData([]);
      return undefined;
    }
    if (!Number.isInteger(range.start) || !Number.isInteger(range.end) || range.start > range.end) {
      setData([]);
      setMessage('The start year must be less than or equal to the end year.');
      return undefined;
    }
    const controller = new AbortController();
    setMessage('');
    setDataLoading(true);
    fetchComparison(
      selectedCountries.map(country => country.value),
      indicator.value,
      range.start,
      range.end,
      controller.signal,
    )
      .then(result => {
        setData(result);
        if (result.length === 0) setMessage('No observations are available for this selection.');
      })
      .catch((error: unknown) => {
        if (!isRequestCanceled(error)) {
          setData([]);
          setMessage(getApiErrorMessage(error, 'Failed to load economic observations.'));
        }
      })
      .finally(() => {
        if (!controller.signal.aborted) setDataLoading(false);
      });
    return () => controller.abort();
  }, [selectedCountries, indicator, range]);

  const series = useMemo<ChartSeries[]>(() => selectedCountries
    .map(country => ({
      name: country.label,
      points: data
        .filter(point => point.country === country.value)
        .map(point => ({ year: point.year, indicatorValue: point.value })),
    }))
    .filter(item => item.points.length > 0), [data, selectedCountries]);

  const primaryData = selectedCountries[0]
    ? data.filter(point => point.country === selectedCountries[0].value).sort((a, b) => a.year - b.year)
    : [];
  const latest = primaryData.at(-1);
  const previous = primaryData.at(-2);
  const change = latest && previous && previous.value !== 0
    ? ((latest.value - previous.value) / Math.abs(previous.value)) * 100
    : undefined;

  const handleForecast = () => {
    if (selectedCountries.length !== 1 || !indicator || data.length === 0) return;
    forecastControllerRef.current?.abort();
    const controller = new AbortController();
    forecastControllerRef.current = controller;
    setForecastLoading(true);
    setMessage('');
    fetchForecastEvaluation(
      selectedCountries[0].value,
      indicator.value,
      range.start,
      range.end,
      horizon,
      controller.signal,
    )
      .then(setForecast)
      .catch((error: unknown) => {
        if (!isRequestCanceled(error)) {
          setForecast(null);
          setMessage(getApiErrorMessage(error, 'Forecast evaluation failed.'));
        }
      })
      .finally(() => {
        if (forecastControllerRef.current === controller) {
          setForecastLoading(false);
          forecastControllerRef.current = null;
        }
      });
  };

  return (
    <div className="app-shell">
      <header className="hero">
        <div>
          <p className="eyebrow">WORLD BANK OPEN DATA · ECONOMIC ANALYTICS</p>
          <h1>Global Economic Observatory</h1>
          <p className="hero-copy">Compare countries, inspect annual evidence, and evaluate bounded forecasts without hiding uncertainty.</p>
        </div>
        <a href="https://data.worldbank.org/" target="_blank" rel="noreferrer" className="source-link">Source: World Bank</a>
      </header>

      <main>
        <section className="panel controls-panel" aria-labelledby="analysis-controls">
          <div className="section-heading">
            <div><p className="eyebrow">ANALYSIS</p><h2 id="analysis-controls">Build a comparison</h2></div>
            <span className="selection-count">{selectedCountries.length}/5 countries</span>
          </div>
          <div className="control-grid">
            <div className="field field-wide"><label htmlFor="country-selector">Countries</label>
              <CountrySelector options={countries} value={selectedCountries} onChange={setSelectedCountries} isLoading={metadataLoading} />
            </div>
            <div className="field field-wide"><label htmlFor="indicator-selector">Indicator</label>
              <IndicatorSelector options={indicators} value={indicator} onChange={setIndicator} onSearch={setIndicatorSearch} isLoading={metadataLoading} />
            </div>
            <label className="field"><span>Start year</span><input aria-label="Start year" type="number" min="1900" max={currentYear + 1} value={range.start} onChange={(event: ChangeEvent<HTMLInputElement>) => setRange(current => ({ ...current, start: Number(event.target.value) }))} /></label>
            <label className="field"><span>End year</span><input aria-label="End year" type="number" min="1900" max={currentYear + 1} value={range.end} onChange={(event: ChangeEvent<HTMLInputElement>) => setRange(current => ({ ...current, end: Number(event.target.value) }))} /></label>
            <label className="field"><span>Forecast horizon</span><select aria-label="Forecast horizon" value={horizon} onChange={event => setHorizon(Number(event.target.value))}>{horizons.map(value => <option key={value} value={value}>{value} year{value === 1 ? '' : 's'}</option>)}</select></label>
          </div>
          <div className="actions">
            <button type="button" className="primary-button" onClick={handleForecast} disabled={selectedCountries.length !== 1 || !indicator || dataLoading || forecastLoading || data.length === 0}>{forecastLoading ? 'Evaluating models…' : 'Evaluate forecast'}</button>
            <ExportCSV data={data} fileName={`${indicator?.value ?? 'economic'}_${selectedCountries.map(item => item.value).join('-') || 'data'}`} disabled={dataLoading || data.length === 0} />
            {selectedCountries.length > 1 && <p className="inline-note">Forecasting is available in single-country mode.</p>}
          </div>
        </section>

        {message && <div className="notice" role="alert">{message}</div>}
        {(dataLoading || metadataLoading) && <div className="loading" role="status">Loading verified World Bank data…</div>}

        <section className="kpi-grid" aria-label="Analysis summary">
          <article className="kpi"><span>Latest value</span><strong>{formatValue(latest?.value)}</strong><small>{latest ? `${selectedCountries[0]?.label} · ${latest.year}` : 'Select an analysis'}</small></article>
          <article className="kpi"><span>Previous-period change</span><strong>{change === undefined ? '—' : `${change >= 0 ? '+' : ''}${change.toFixed(2)}%`}</strong><small>{previous && latest ? `${previous.year} to ${latest.year}` : 'Requires two observations'}</small></article>
          <article className="kpi"><span>Selected model</span><strong>{forecast?.evaluation.selected_model ?? '—'}</strong><small>{forecast ? `${forecast.evaluation.validation_points}-year holdout` : 'Evaluate a single country'}</small></article>
          <article className="kpi"><span>Validation MAE</span><strong>{formatMetric(forecast?.evaluation.model_metrics.mae)}</strong><small>{forecast?.evaluation.beats_baseline ? 'Beat the baseline' : forecast ? 'Baseline remained competitive' : 'Chronological validation'}</small></article>
        </section>

        <section className="analysis-grid">
          <article className="panel chart-panel">
            <div className="section-heading"><div><p className="eyebrow">EVIDENCE & ESTIMATE</p><h2>{indicator?.label ?? 'Economic series'}</h2></div>{latest && <span className="latest-year">Latest observed: {latest.year}</span>}</div>
            {series.length > 0 ? <Suspense fallback={<p>Loading chart…</p>}><LineChart series={series} forecast={forecast} title="Annual observations and evaluated forecast" yAxisTitle={indicator?.label ?? 'Value'} /></Suspense> : <div className="empty-state">Choose countries and an indicator to begin.</div>}
            {forecast?.warnings.map(warning => <p className="model-warning" key={warning}>{warning}</p>)}
          </article>
          <aside className="panel map-panel"><div className="section-heading"><div><p className="eyebrow">GEOGRAPHY</p><h2>Selected context</h2></div></div>{selectedCountries[0] ? <Suspense fallback={<p>Loading map…</p>}><MapChart country={selectedCountries[0]} /></Suspense> : <div className="empty-state compact">No country selected.</div>}</aside>
        </section>
      </main>
      <footer>Historical values are World Bank observations. Forecasts are statistical estimates with uncertainty, not facts.</footer>
    </div>
  );
}
