import type { IndicatorPoint } from './types';

const FORMULA_PREFIX = /^[\t\r\n ]*[=+\-@]/;
const COLUMNS = ['country', 'indicator', 'year', 'value'] as const;

function quoteText(value: string): string {
  const safeValue = FORMULA_PREFIX.test(value) ? `'${value}` : value;
  return `"${safeValue.replaceAll('"', '""')}"`;
}

function serializeCell(value: string | number): string {
  if (typeof value === 'number') {
    return Number.isFinite(value) ? String(value) : '';
  }
  return quoteText(value);
}

export function serializeIndicatorCsv(data: IndicatorPoint[]): string {
  const rows = [
    COLUMNS.join(','),
    ...data.map(point => COLUMNS.map(column => serializeCell(point[column])).join(',')),
  ];
  return `\uFEFF${rows.join('\r\n')}`;
}

export function safeCsvFileName(value: string): string {
  const sanitized = value.replace(/[^A-Za-z0-9._-]/g, '_').replace(/^\.+/, '');
  return sanitized || 'economic_data';
}
