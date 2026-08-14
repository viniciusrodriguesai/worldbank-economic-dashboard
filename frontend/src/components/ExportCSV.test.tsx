import { fireEvent, render, screen } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import ExportCSV from './ExportCSV';

describe('ExportCSV', () => {
  const createObjectURL = vi.fn(() => 'blob:download');
  const revokeObjectURL = vi.fn();
  const click = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
    Object.defineProperty(URL, 'createObjectURL', { configurable: true, value: createObjectURL });
    Object.defineProperty(URL, 'revokeObjectURL', { configurable: true, value: revokeObjectURL });
    vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(click);
  });

  it('creates and immediately revokes a sanitized CSV download', () => {
    render(
      <ExportCSV
        data={[{ country: 'BRA', indicator: 'GDP', year: 2024, value: -2 }]}
        fileName="../GDP report"
      />,
    );
    fireEvent.click(screen.getByRole('button', { name: 'Export CSV' }));
    expect(createObjectURL).toHaveBeenCalledOnce();
    expect(click).toHaveBeenCalledOnce();
    expect(revokeObjectURL).toHaveBeenCalledWith('blob:download');
  });

  it('stays disabled for an empty dataset', () => {
    render(<ExportCSV data={[]} fileName="empty" disabled />);
    expect(screen.getByRole('button', { name: 'Export CSV' })).toBeDisabled();
  });
});
