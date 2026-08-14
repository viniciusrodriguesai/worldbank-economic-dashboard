import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import type { CountryOption, IndicatorOption } from '../types';

const apiMocks = vi.hoisted(() => ({
  fetchCountries: vi.fn(),
  fetchData: vi.fn(),
  fetchForecast: vi.fn(),
  fetchIndicators: vi.fn(),
}));

vi.mock('../api', () => ({
  ...apiMocks,
  getApiErrorMessage: (error: unknown) => (
    error instanceof Error ? error.message : 'Request failed'
  ),
  isRequestCanceled: () => false,
}));

vi.mock('../components/CountrySelector', () => ({
  default: ({
    options,
    value,
    onChange,
  }: {
    options: CountryOption[];
    value: CountryOption | null;
    onChange: (option: CountryOption | null) => void;
  }) => (
    <select
      aria-label="Country selector"
      value={value?.value ?? ''}
      onChange={event => (
        onChange(options.find(option => option.value === event.target.value) ?? null)
      )}
    >
      <option value="">Select a country</option>
      {options.map(option => (
        <option key={option.value} value={option.value}>{option.label}</option>
      ))}
    </select>
  ),
}));

vi.mock('../components/IndicatorSelector', () => ({
  default: ({
    options,
    value,
    onChange,
  }: {
    options: IndicatorOption[];
    value: IndicatorOption | null;
    onChange: (option: IndicatorOption | null) => void;
  }) => (
    <select
      aria-label="Indicator selector"
      value={value?.value ?? ''}
      onChange={event => (
        onChange(options.find(option => option.value === event.target.value) ?? null)
      )}
    >
      <option value="">Select an indicator</option>
      {options.map(option => (
        <option key={option.value} value={option.value}>{option.label}</option>
      ))}
    </select>
  ),
}));

vi.mock('../components/MapChart', () => ({
  default: () => <div>Country map</div>,
}));

vi.mock('../components/LineChart', () => ({
  default: ({ title }: { title: string }) => <div>{title}</div>,
}));

import Dashboard from './Dashboard';

describe('Dashboard', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    apiMocks.fetchCountries.mockResolvedValue([
      { value: 'BRA', label: 'Brazil', iso2Code: 'BR' },
    ]);
    apiMocks.fetchIndicators.mockResolvedValue([
      { value: 'NY.GDP.MKTP.CD', label: 'GDP (current US$)' },
    ]);
    apiMocks.fetchData.mockResolvedValue([
      {
        country: 'Brazil',
        indicator: 'NY.GDP.MKTP.CD',
        year: 2022,
        value: 1.92e12,
      },
    ]);
    apiMocks.fetchForecast.mockResolvedValue([
      {
        country: 'BRA',
        indicator: 'NY.GDP.MKTP.CD',
        year: 2023,
        value: 2.01e12,
      },
    ]);
  });

  it('loads selected data and generates a forecast with the visible range', async () => {
    const user = userEvent.setup();
    render(<Dashboard />);

    await waitFor(() => {
      expect(apiMocks.fetchCountries).toHaveBeenCalledOnce();
      expect(apiMocks.fetchIndicators).toHaveBeenCalledOnce();
    });

    fireEvent.change(screen.getByLabelText('Country selector'), {
      target: { value: 'BRA' },
    });
    fireEvent.change(screen.getByLabelText('Indicator selector'), {
      target: { value: 'NY.GDP.MKTP.CD' },
    });

    await waitFor(() => {
      expect(apiMocks.fetchData).toHaveBeenCalledWith(
        'BRA',
        'NY.GDP.MKTP.CD',
        2000,
        2022,
        expect.any(AbortSignal),
      );
    });
    expect(await screen.findByText('Historical Data')).toBeInTheDocument();

    await user.click(screen.getByRole('button', {
      name: 'Generate 5-Year Forecast',
    }));

    await waitFor(() => {
      expect(apiMocks.fetchForecast).toHaveBeenCalledWith(
        'BRA',
        'NY.GDP.MKTP.CD',
        2000,
        2022,
        5,
        expect.any(AbortSignal),
      );
    });
    expect(await screen.findByText('5-Year Forecast')).toBeInTheDocument();
  });

  it('does not request data when the period is reversed', async () => {
    render(<Dashboard />);

    await screen.findByRole('option', { name: 'Brazil' });
    fireEvent.change(screen.getByLabelText('Country selector'), {
      target: { value: 'BRA' },
    });
    fireEvent.change(screen.getByLabelText('Indicator selector'), {
      target: { value: 'NY.GDP.MKTP.CD' },
    });
    fireEvent.change(screen.getByLabelText('From:'), {
      target: { value: '2023' },
    });

    expect(await screen.findByText(
      'The start year must be less than or equal to the end year.',
    )).toBeInTheDocument();
  });
});
