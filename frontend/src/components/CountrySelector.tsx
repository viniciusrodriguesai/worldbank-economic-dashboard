import Select from 'react-select';
import type { CountryOption } from '../types';

interface CountrySelectorProps {
  options: CountryOption[];
  value: CountryOption[];
  onChange: (value: CountryOption[]) => void;
  isLoading?: boolean;
}

export default function CountrySelector({
  options,
  value,
  onChange,
  isLoading = false,
}: CountrySelectorProps) {
  return (
    <Select<CountryOption, true>
      options={options}
      value={value}
      onChange={selected => onChange([...selected])}
      isLoading={isLoading}
      placeholder="Select up to 5 countries"
      isMulti
      closeMenuOnSelect={false}
      isOptionDisabled={() => value.length >= 5}
      aria-label="Countries"
      classNamePrefix="select"
    />
  );
}
