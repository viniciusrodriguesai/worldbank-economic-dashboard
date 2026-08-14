import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import type { CountryOption, IndicatorOption } from '../types';

const apiMocks = vi.hoisted(() => ({
  fetchCountries: vi.fn(),
  fetchComparison: vi.fn(),
  fetchData: vi.fn(),
  fetchForecast: vi.fn(),
  fetchForecastEvaluation: vi.fn(),
  fetchIndicators: vi.fn(),
}));

const currentYear = new Date().getFullYear();

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
    value: CountryOption[];
    onChange: (option: CountryOption[]) => void;
  }) => (
    <select
      aria-label="Country selector"
      value={value[0]?.value ?? ''}
      onChange={event => (
        onChange(options.filter(option => option.value === event.target.value))
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
    apiMocks.fetchComparison.mockResolvedValue([
      {
        country: 'BRA',
        indicator: 'NY.GDP.MKTP.CD',
        year: 2022,
        value: 1.92e12,
      },
    ]);
    apiMocks.fetchForecastEvaluation.mockResolvedValue({
      history: [],
      forecast: [{
        country: 'BRA', indicator: 'NY.GDP.MKTP.CD', year: currentYear + 1,
        value: 2.01e12, lower_bound: 1.9e12, upper_bound: 2.1e12,
      }],
      evaluation: {
        selected_model: 'drift', selected_order: null, validation_points: 3,
        model_metrics: { mae: 1, rmse: 1.2, mape: 2, smape: 2 },
        baseline_model: 'drift', baseline_metrics: { mae: 1, rmse: 1.2, mape: 2, smape: 2 },
        beats_baseline: false,
      },
      horizon: 5,
      missing_years: [],
      warnings: [],
    });
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
      expect(apiMocks.fetchComparison).toHaveBeenCalledWith(
        ['BRA'],
        'NY.GDP.MKTP.CD',
        currentYear - 20,
        currentYear,
        expect.any(AbortSignal),
      );
    });
    expect(await screen.findByText('Annual observations and evaluated forecast')).toBeInTheDocument();

    await user.click(screen.getByRole('button', {
      name: 'Evaluate forecast',
    }));

    await waitFor(() => {
      expect(apiMocks.fetchForecastEvaluation).toHaveBeenCalledWith(
        'BRA',
        'NY.GDP.MKTP.CD',
        currentYear - 20,
        currentYear,
        5,
        expect.any(AbortSignal),
      );
    });
    expect(await screen.findByText('drift')).toBeInTheDocument();
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
    await waitFor(() => expect(apiMocks.fetchComparison).toHaveBeenCalled());
    apiMocks.fetchComparison.mockClear();
    fireEvent.change(screen.getByLabelText('Start year'), {
      target: { value: String(currentYear + 1) },
    });

    expect(await screen.findByText(
      'The start year must be less than or equal to the end year.',
    )).toBeInTheDocument();
    expect(apiMocks.fetchComparison).not.toHaveBeenCalled();
  });
});
