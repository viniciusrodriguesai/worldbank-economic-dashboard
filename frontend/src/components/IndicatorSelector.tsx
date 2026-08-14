import Select from 'react-select';
import type { IndicatorOption } from '../types';

interface IndicatorSelectorProps {
  options: IndicatorOption[];
  value: IndicatorOption | null;
  onChange: (value: IndicatorOption | null) => void;
  onSearch?: (value: string) => void;
  isLoading?: boolean;
}

export default function IndicatorSelector({
  options,
  value,
  onChange,
  onSearch,
  isLoading = false,
}: IndicatorSelectorProps) {
  return (
    <Select<IndicatorOption>
      options={options}
      value={value}
      onChange={onChange}
      isLoading={isLoading}
      placeholder="Select an indicator"
      isClearable
      onInputChange={value => onSearch?.(value)}
      aria-label="Economic indicator"
      classNamePrefix="select"
    />
  );
}
