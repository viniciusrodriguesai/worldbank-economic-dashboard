// src/components/CountrySelector.jsx

import React from "react";
import Select from "react-select";

export default function CountrySelector({ options, value, onChange, isLoading = false }) {
  return (
    <Select
      options={options}
      value={value}
      onChange={onChange}
      isLoading={isLoading}
      placeholder="Select a country"
      isClearable
      aria-label="Country selector"
      styles={{
        container: (base) => ({
          ...base,
          width: 300,
        }),
      }}
    />
  );
}
