import Plotly from 'plotly.js-basic-dist-min';
import createPlotlyComponent from 'react-plotly.js/factory';
import type { ChartPoint } from '../types';

const Plot = createPlotlyComponent(Plotly);

interface LineChartProps {
  data: ChartPoint[];
  title?: string;
}

export default function LineChart({
  data,
  title = 'Trend Over Time',
}: LineChartProps) {
  if (data.length === 0) {
    return null;
  }

  return (
    <Plot
      data={[
        {
          x: data.map(point => point.year),
          y: data.map(point => point.indicatorValue),
          type: 'scatter',
          mode: 'lines+markers',
          marker: { color: '#2563eb' },
          name: title,
        },
      ]}
      layout={{
        title: { text: title },
        xaxis: { title: { text: 'Year' } },
        yaxis: { title: { text: title } },
        margin: { t: 50, l: 60, r: 30, b: 50 },
        autosize: true,
      }}
      style={{ width: '100%', height: '400px' }}
      config={{ responsive: true, displaylogo: false }}
      useResizeHandler
    />
  );
}
