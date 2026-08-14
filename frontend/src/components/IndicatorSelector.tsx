import Select from 'react-select';
import type { IndicatorOption } from '../types';

interface IndicatorSelectorProps {
  options: IndicatorOption[];
  value: IndicatorOption | null;
  onChange: (value: IndicatorOption | null) => void;
  isLoading?: boolean;
}

export default function IndicatorSelector({
  options,
  value,
  onChange,
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
      aria-label="Indicator selector"
      styles={{
        container: base => ({
          ...base,
          width: 300,
        }),
      }}
    />
  );
}
