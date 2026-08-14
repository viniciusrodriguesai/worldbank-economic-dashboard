import { beforeEach, describe, expect, it, vi } from 'vitest';

const { getMock } = vi.hoisted(() => ({
  getMock: vi.fn(),
}));

vi.mock('axios', () => ({
  default: {
    create: () => ({ get: getMock }),
    isCancel: () => false,
    isAxiosError: (error: unknown) => (
      typeof error === 'object'
      && error !== null
      && 'isAxiosError' in error
    ),
  },
}));

import {
  fetchCountries,
  fetchComparison,
  fetchData,
  fetchForecast,
  fetchForecastEvaluation,
  fetchIndicators,
  getApiErrorMessage,
} from './api';

describe('API client', () => {
  beforeEach(() => {
    getMock.mockReset();
  });

  it('maps API countries to typed selector options', async () => {
    getMock.mockResolvedValue({
      data: [
        {
          id: 'BRA',
          iso2Code: 'BR',
          name: 'Brazil',
          region: 'Latin America & Caribbean',
          capitalCity: 'Brasilia',
        },
      ],
    });

    await expect(fetchCountries()).resolves.toEqual([
      { value: 'BRA', label: 'Brazil', iso2Code: 'BR' },
    ]);
  });

  it('sends start and end parameters and returns the data array', async () => {
    const points = [
      {
        country: 'Brazil',
        indicator: 'NY.GDP.MKTP.CD',
        year: 2020,
        value: 1.48e12,
      },
    ];
    getMock.mockResolvedValue({ data: points });

    await expect(
      fetchData('BRA', 'NY.GDP.MKTP.CD', 2010, 2020),
    ).resolves.toEqual(points);

    expect(getMock).toHaveBeenCalledWith('/data', {
      params: {
        country: 'BRA',
        indicator: 'NY.GDP.MKTP.CD',
        start: 2010,
        end: 2020,
      },
      signal: undefined,
    });
  });

  it('requests a bounded indicator search', async () => {
    getMock.mockResolvedValue({ data: [{ id: 'NY.GDP.MKTP.CD', name: 'GDP' }] });
    await fetchIndicators('gdp');
    expect(getMock).toHaveBeenCalledWith('/indicators', {
      params: { search: 'gdp', limit: 50, offset: 0 },
      signal: undefined,
    });
  });

  it('serializes repeated country parameters for comparison', async () => {
    getMock.mockResolvedValue({ data: [] });
    await fetchComparison(['BRA', 'USA'], 'GDP', 2000, 2020);
    const request = getMock.mock.calls[0][1];
    expect(request.params.getAll('countries')).toEqual(['BRA', 'USA']);
    expect(request.params.get('indicator')).toBe('GDP');
  });

  it('sends the selected fitting period to the forecast endpoint', async () => {
    getMock.mockResolvedValue({ data: [] });

    await fetchForecast('BRA', 'NY.GDP.MKTP.CD', 2000, 2022, 5);

    expect(getMock).toHaveBeenCalledWith('/forecast', {
      params: {
        country: 'BRA',
        indicator: 'NY.GDP.MKTP.CD',
        start: 2000,
        end: 2022,
        years_ahead: 5,
      },
      signal: undefined,
    });
  });

  it('requests typed forecast evaluation metadata', async () => {
    getMock.mockResolvedValue({ data: { forecast: [] } });
    await fetchForecastEvaluation('BRA', 'GDP', 2000, 2022, 3);
    expect(getMock).toHaveBeenCalledWith('/forecast/evaluate', {
      params: {
        country: 'BRA',
        indicator: 'GDP',
        start: 2000,
        end: 2022,
        years_ahead: 3,
      },
      signal: undefined,
    });
  });

  it('extracts FastAPI validation messages', () => {
    const error = {
      isAxiosError: true,
      response: {
        data: {
          detail: [{ msg: 'Country code must contain three characters.' }],
        },
      },
      message: 'Request failed',
    };

    expect(getApiErrorMessage(error)).toBe(
      'Country code must contain three characters.',
    );
  });
});
