import { describe, expect, it } from 'vitest';

import { safeCsvFileName, serializeIndicatorCsv } from './csv';

describe('secure CSV serialization', () => {
  it('neutralizes formulas in text while preserving negative numbers', () => {
    const csv = serializeIndicatorCsv([
      {
        country: '=WEBSERVICE("https://example.invalid")',
        indicator: '@SUM(A1)',
        year: 2024,
        value: -42.5,
      },
    ]);

    expect(csv).toContain('"\'=WEBSERVICE(""https://example.invalid"")"');
    expect(csv).toContain('"\'@SUM(A1)"');
    expect(csv).toContain('2024,-42.5');
  });

  it('quotes delimiters and uses deterministic columns and CRLF rows', () => {
    const csv = serializeIndicatorCsv([
      { country: 'Congo, Dem. Rep.', indicator: 'GDP "real"', year: 2023, value: 12 },
    ]);

    expect(csv).toBe(
      '\uFEFFcountry,indicator,year,value\r\n'
      + '"Congo, Dem. Rep.","GDP ""real""",2023,12',
    );
  });

  it('sanitizes unsafe download names', () => {
    expect(safeCsvFileName('../../report:2024')).toBe('_.._report_2024');
  });
});
