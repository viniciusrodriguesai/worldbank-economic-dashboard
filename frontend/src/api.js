// src/api.js

import axios from 'axios';

// Create an axios instance with a 20-second timeout and base URL
const apiClient = axios.create({
  baseURL: '/',       // Uses proxy in package.json pointing to http://localhost:8000
  timeout: 20000,     // 20 seconds timeout
});

/**
 * Fetch the list of countries from the backend.
 * @returns {Promise<Array<{value: string, label: string}>>}
 */
export async function fetchCountries() {
  const res = await apiClient.get('/countries');
  return res.data.map(c => ({ value: c.id, label: c.name }));
}

/**
 * Fetch the list of indicators from the backend.
 * @returns {Promise<Array<{value: string, label: string}>>}
 */
export async function fetchIndicators() {
  const res = await apiClient.get('/indicators');
  return res.data.map(i => ({ value: i.id, label: i.name }));
}

/**
 * Fetch historical data for a given country and indicator.
 * @param {string} countryCode - ISO code of the country.
 * @param {string} indicatorCode - World Bank indicator code.
 * @param {number} startYear - Start year for data.
 * @param {number} endYear - End year for data.
 * @returns {Promise<{status: number, data?: Array<{year: number, value: number}>}>}
 */
export async function fetchData(countryCode, indicatorCode, startYear, endYear) {
  const res = await apiClient.get('/data', {
    params: { country: countryCode, indicator: indicatorCode, start: startYear, end: endYear },
    validateStatus: () => true, // allow handling of 400
  });

  if (res.status === 200) {
    return { status: 200, data: res.data };
  }
  if (res.status === 400) {
    return { status: 400 };
  }
  throw new Error(`Unexpected status code: ${res.status}`);
}

/**
 * Fetch forecast data for a given country and indicator.
 * @param {string} countryCode - ISO code of the country.
 * @param {string} indicatorCode - World Bank indicator code.
 * @param {number} yearsAhead - Number of years to forecast.
 * @returns {Promise<{status: number, data?: Array<{year: number, forecast: number}>}>}
 */
export async function fetchForecast(countryCode, indicatorCode, yearsAhead) {
  const res = await apiClient.get('/forecast', {
    params: { country: countryCode, indicator: indicatorCode, years_ahead: yearsAhead },
    validateStatus: () => true,
  });

  if (res.status === 200) {
    return { status: 200, data: res.data };
  }
  if (res.status === 400) {
    return { status: 400 };
  }
  throw new Error(`Unexpected status code: ${res.status}`);
}
