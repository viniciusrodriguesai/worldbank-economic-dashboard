// src/pages/Dashboard.jsx

import React, { useState, useEffect } from 'react';
import CountrySelector from '../components/CountrySelector';
import IndicatorSelector from '../components/IndicatorSelector';
import LineChart from '../components/LineChart';
import ExportCSV from '../components/ExportCSV';
import { fetchCountries, fetchIndicators, fetchData, fetchForecast } from '../api';

export default function Dashboard() {
  const [countries, setCountries] = useState([]);
  const [indicators, setIndicators] = useState([]);
  const [country, setCountry] = useState(null);
  const [indicator, setIndicator] = useState(null);
  const [range, setRange] = useState({ start: 2000, end: 2022 });
  const [data, setData] = useState([]);
  const [forecast, setForecast] = useState([]);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState('');

  // Load countries and indicators once
  useEffect(() => {
    fetchCountries()
      .then(setCountries)
      .catch(err => console.error('Error loading countries:', err));

    fetchIndicators()
      .then(setIndicators)
      .catch(err => console.error('Error loading indicators:', err));
  }, []);

  // Fetch historical data when selections or range change
  useEffect(() => {
    if (!country || !indicator) return;

    setMessage('');
    setLoading(true);

    fetchData(country.value, indicator.value, range.start, range.end)
      .then(result => {
        if (!result || result.length === 0) {
          setData([]);
          setMessage('No data available for the selected parameters.');
        } else {
          setData(result);
        }
      })
      .catch(err => {
        console.error('Error fetching data:', err);
        setData([]);
        setMessage(`Failed to load data: ${err.message}`);
      })
      .finally(() => setLoading(false));
  }, [country, indicator, range]);

  // Handle forecast generation
  const handleForecast = () => {
    if (!country || !indicator || data.length === 0) return;

    setMessage('');
    setLoading(true);

    fetchForecast(country.value, indicator.value, range.start, range.end, 5)
      .then(fc => {
        if (!fc || fc.length === 0) {
          setForecast([]);
          setMessage('No forecast data available.');
        } else {
          setForecast(fc);
        }
      })
      .catch(err => {
        console.error('Error generating forecast:', err);
        setForecast([]);
        setMessage(`Failed to generate forecast: ${err.message}`);
      })
      .finally(() => setLoading(false));
  };

  return (
    <div style={{ padding: 20 }}>
      <h1>📊 Economic Dashboard</h1>

      <div style={{ display: 'flex', gap: 16, marginBottom: 20 }}>
        <CountrySelector options={countries} value={country} onChange={setCountry} />
        <IndicatorSelector options={indicators} value={indicator} onChange={setIndicator} />
      </div>

      <div style={{ display: 'flex', gap: 16, marginBottom: 20 }}>
        <label>
          From:
          <input
            type="number"
            value={range.start}
            onChange={e => setRange(r => ({ ...r, start: +e.target.value }))}
            style={{ width: 80, marginLeft: 8 }}
          />
        </label>
        <label>
          To:
          <input
            type="number"
            value={range.end}
            onChange={e => setRange(r => ({ ...r, end: +e.target.value }))}
            style={{ width: 80, marginLeft: 8 }}
          />
        </label>
      </div>

      <button
        onClick={handleForecast}
        disabled={!country || !indicator || loading || data.length === 0}
        style={{ marginBottom: 20 }}
      >
        {loading ? 'Loading...' : 'Generate 5-Year Forecast'}
      </button>

      <ExportCSV
        data={data}
        fileName="historical_data"
        disabled={loading || data.length === 0}
      />

      {message && (
        <div style={{ color: 'red', marginBottom: 20 }}>
          {message}
        </div>
      )}

      {loading && (
        <p style={{ fontStyle: 'italic', marginBottom: 20 }}>Carregando dados...</p>
      )}

      {data.length > 0 && !loading && (
        <LineChart
          data={data.map(d => ({ year: d.year, indicator_value: d.value }))}
          title="Historical Data"
        />
      )}

      {forecast.length > 0 && !loading && (
        <LineChart
          data={forecast.map(d => ({ year: d.year, indicator_value: d.forecast ?? d.value }))}
          title="5-Year Forecast"
        />
      )}
    </div>
  );
}
