import Select from 'react-select';
import type { CountryOption } from '../types';

interface CountrySelectorProps {
  options: CountryOption[];
  value: CountryOption | null;
  onChange: (value: CountryOption | null) => void;
  isLoading?: boolean;
}

export default function CountrySelector({
  options,
  value,
  onChange,
  isLoading = false,
}: CountrySelectorProps) {
  return (
    <Select<CountryOption>
      options={options}
      value={value}
      onChange={onChange}
      isLoading={isLoading}
      placeholder="Select a country"
      isClearable
      aria-label="Country selector"
      styles={{
        container: base => ({
          ...base,
          width: 300,
        }),
      }}
    />
  );
}
