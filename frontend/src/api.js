// src/api.js

import axios from 'axios';

// Create an axios instance with a 20-second timeout and base URL
const apiClient = axios.create({
  baseURL: '/',       // Uses proxy in package.json pointing to http://localhost:8000
  timeout: 20000,     // 20 seconds timeout
});

export function isRequestCanceled(error) {
  return axios.isCancel(error) || error?.code === 'ERR_CANCELED';
}

export function getApiErrorMessage(error, fallback = 'Unable to complete the request.') {
  const detail = error?.response?.data?.detail;

  if (typeof detail === 'string') {
    return detail;
  }

  if (Array.isArray(detail)) {
    return detail.map(item => item.msg).filter(Boolean).join(' ');
  }

  if (error?.code === 'ECONNABORTED') {
    return 'The request timed out. Please try again.';
  }

  return error?.message || fallback;
}

/**
 * Fetch the list of countries from the backend.
 * @returns {Promise<Array<{value: string, label: string}>>}
 */
export async function fetchCountries(signal) {
  const res = await apiClient.get('/countries', { signal });
  return res.data.map(c => ({ value: c.id, label: c.name, iso2Code: c.iso2Code }));
}

/**
 * Fetch the list of indicators from the backend.
 * @returns {Promise<Array<{value: string, label: string}>>}
 */
export async function fetchIndicators(signal) {
  const res = await apiClient.get('/indicators', { signal });
  return res.data.map(i => ({ value: i.id, label: i.name }));
}

/**
 * Fetch historical data for a given country and indicator.
 * @param {string} countryCode - ISO code of the country.
 * @param {string} indicatorCode - World Bank indicator code.
 * @param {number} startYear - Start year for data.
 * @param {number} endYear - End year for data.
 * @returns {Promise<Array<{year: number, value: number}>>}
 */
export async function fetchData(countryCode, indicatorCode, startYear, endYear, signal) {
  const res = await apiClient.get('/data', {
    params: { country: countryCode, indicator: indicatorCode, start: startYear, end: endYear },
    signal,
  });
  return res.data;
}

/**
 * Fetch forecast data for a given country and indicator.
 * @param {string} countryCode - ISO code of the country.
 * @param {string} indicatorCode - World Bank indicator code.
 * @param {number} startYear - First year used to fit the model.
 * @param {number} endYear - Last year used to fit the model.
 * @param {number} yearsAhead - Number of years to forecast.
 * @returns {Promise<Array<{year: number, value: number}>>}
 */
export async function fetchForecast(
  countryCode,
  indicatorCode,
  startYear,
  endYear,
  yearsAhead,
  signal,
) {
  const res = await apiClient.get('/forecast', {
    params: {
      country: countryCode,
      indicator: indicatorCode,
      start: startYear,
      end: endYear,
      years_ahead: yearsAhead,
    },
    signal,
  });
  return res.data;
}
