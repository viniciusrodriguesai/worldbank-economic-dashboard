// src/components/IndicatorSelector.jsx

import React from "react";
import Select from "react-select";

export default function IndicatorSelector({ options, value, onChange, isLoading = false }) {
  return (
    <Select
      options={options}
      value={value}
      onChange={onChange}
      isLoading={isLoading}
      placeholder="Select an indicator"
      isClearable
      aria-label="Indicator selector"
      styles={{
        container: (base) => ({
          ...base,
          width: 300,
        }),
      }}
    />
  );
}
