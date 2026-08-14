import React, { lazy, Suspense, useEffect, useRef, useState } from 'react';
import type { ChangeEvent } from 'react';
import CountrySelector from '../components/CountrySelector';
import IndicatorSelector from '../components/IndicatorSelector';
import ExportCSV from '../components/ExportCSV';
import {
  fetchCountries,
  fetchData,
  fetchForecast,
  fetchIndicators,
  getApiErrorMessage,
  isRequestCanceled,
} from '../api';
import type {
  CountryOption,
  IndicatorOption,
  IndicatorPoint,
} from '../types';

const LineChart = lazy(() => import('../components/LineChart'));
const MapChart = lazy(() => import('../components/MapChart'));

export default function Dashboard() {
  const [countries, setCountries] = useState<CountryOption[]>([]);
  const [indicators, setIndicators] = useState<IndicatorOption[]>([]);
  const [country, setCountry] = useState<CountryOption | null>(null);
  const [indicator, setIndicator] = useState<IndicatorOption | null>(null);
  const [range, setRange] = useState({ start: 2000, end: 2022 });
  const [data, setData] = useState<IndicatorPoint[]>([]);
  const [forecast, setForecast] = useState<IndicatorPoint[]>([]);
  const [metadataLoading, setMetadataLoading] = useState(true);
  const [dataLoading, setDataLoading] = useState(false);
  const [forecastLoading, setForecastLoading] = useState(false);
  const [message, setMessage] = useState('');
  const forecastControllerRef = useRef<AbortController | null>(null);

  // Load countries and indicators once
  useEffect(() => {
    const controller = new AbortController();
    setMetadataLoading(true);

    Promise.all([
      fetchCountries(controller.signal),
      fetchIndicators(controller.signal),
    ])
      .then(([countryOptions, indicatorOptions]) => {
        setCountries(countryOptions);
        setIndicators(indicatorOptions);
      })
      .catch((error: unknown) => {
        if (!isRequestCanceled(error)) {
          setMessage(getApiErrorMessage(error, 'Failed to load filters.'));
        }
      })
      .finally(() => {
        if (!controller.signal.aborted) {
          setMetadataLoading(false);
        }
      });

    return () => controller.abort();
  }, []);

  // Fetch historical data when selections or range change
  useEffect(() => {
    forecastControllerRef.current?.abort();
    setForecast([]);

    if (!country || !indicator) {
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

    fetchData(country.value, indicator.value, range.start, range.end, controller.signal)
      .then(result => {
        if (result.length === 0) {
          setData([]);
          setMessage('No data available for the selected parameters.');
        } else {
          setData(result);
        }
      })
      .catch((error: unknown) => {
        if (!isRequestCanceled(error)) {
          setData([]);
          setMessage(getApiErrorMessage(error, 'Failed to load data.'));
        }
      })
      .finally(() => {
        if (!controller.signal.aborted) {
          setDataLoading(false);
        }
      });

    return () => controller.abort();
  }, [country, indicator, range]);

  // Handle forecast generation
  const handleForecast = () => {
    if (!country || !indicator || data.length === 0) return;

    forecastControllerRef.current?.abort();
    const controller = new AbortController();
    forecastControllerRef.current = controller;
    setMessage('');
    setForecastLoading(true);

    fetchForecast(
      country.value,
      indicator.value,
      range.start,
      range.end,
      5,
      controller.signal,
    )
      .then(fc => {
        if (fc.length === 0) {
          setForecast([]);
          setMessage('No forecast data available.');
        } else {
          setForecast(fc);
        }
      })
      .catch((error: unknown) => {
        if (!isRequestCanceled(error)) {
          setForecast([]);
          setMessage(getApiErrorMessage(error, 'Failed to generate forecast.'));
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
    <div style={{ padding: 20 }}>
      <h1>Economic Dashboard</h1>

      <div style={{ display: 'flex', gap: 16, marginBottom: 20 }}>
        <CountrySelector
          options={countries}
          value={country}
          onChange={setCountry}
          isLoading={metadataLoading}
        />
        <IndicatorSelector
          options={indicators}
          value={indicator}
          onChange={setIndicator}
          isLoading={metadataLoading}
        />
      </div>

      {country && (
        <Suspense fallback={<p>Loading map...</p>}>
          <MapChart country={country} />
        </Suspense>
      )}

      <div style={{ display: 'flex', gap: 16, marginBottom: 20 }}>
        <label>
          From:
          <input
            type="number"
            value={range.start}
            onChange={(event: ChangeEvent<HTMLInputElement>) => (
              setRange(current => ({ ...current, start: Number(event.target.value) }))
            )}
            style={{ width: 80, marginLeft: 8 }}
          />
        </label>
        <label>
          To:
          <input
            type="number"
            value={range.end}
            onChange={(event: ChangeEvent<HTMLInputElement>) => (
              setRange(current => ({ ...current, end: Number(event.target.value) }))
            )}
            style={{ width: 80, marginLeft: 8 }}
          />
        </label>
      </div>

      <button
        onClick={handleForecast}
        disabled={!country || !indicator || dataLoading || forecastLoading || data.length === 0}
        style={{ marginBottom: 20 }}
      >
        {forecastLoading ? 'Generating...' : 'Generate 5-Year Forecast'}
      </button>

      <ExportCSV
        data={data}
        fileName="historical_data"
        disabled={dataLoading || data.length === 0}
      />

      {message && (
        <div style={{ color: 'red', marginBottom: 20 }}>
          {message}
        </div>
      )}

      {dataLoading && (
        <p style={{ fontStyle: 'italic', marginBottom: 20 }}>Loading data...</p>
      )}

      <Suspense fallback={<p>Loading chart...</p>}>
        {data.length > 0 && (
          <LineChart
            data={data.map(point => ({
              year: point.year,
              indicatorValue: point.value,
            }))}
            title="Historical Data"
          />
        )}

        {forecast.length > 0 && (
          <LineChart
            data={forecast.map(point => ({
              year: point.year,
              indicatorValue: point.value,
            }))}
            title="5-Year Forecast"
          />
        )}
      </Suspense>
    </div>
  );
}
