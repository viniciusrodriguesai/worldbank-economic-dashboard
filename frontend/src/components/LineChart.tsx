import Plotly from 'plotly.js-basic-dist-min';
import createPlotlyComponent from 'react-plotly.js/factory';
import type { Data } from 'plotly.js-basic-dist-min';
import type { ChartSeries, ForecastResponse } from '../types';

const Plot = createPlotlyComponent(Plotly);

interface LineChartProps {
  series: ChartSeries[];
  forecast?: ForecastResponse | null;
  title?: string;
  yAxisTitle?: string;
}

const colors = ['#0f766e', '#2563eb', '#c2410c', '#7c3aed', '#be123c'];

export default function LineChart({
  series,
  forecast = null,
  title = 'Trend Over Time',
  yAxisTitle = 'Value',
}: LineChartProps) {
  if (series.length === 0) {
    return null;
  }

  const traces: Data[] = series.map((item, index) => ({
    x: item.points.map(point => point.year),
    y: item.points.map(point => point.indicatorValue),
    type: 'scatter',
    mode: 'lines+markers',
    line: { color: colors[index % colors.length], width: 2.5 },
    marker: { color: colors[index % colors.length], size: 6 },
    name: `${item.name} · historical`,
  }));

  if (forecast?.forecast.length) {
    const points = forecast.forecast;
    traces.push(
      {
        x: points.map(point => point.year),
        y: points.map(point => point.lower_bound),
        type: 'scatter',
        mode: 'lines',
        line: { color: 'rgba(15,118,110,0)' },
        hoverinfo: 'skip',
        showlegend: false,
        name: '95% lower bound',
      },
      {
        x: points.map(point => point.year),
        y: points.map(point => point.upper_bound),
        type: 'scatter',
        mode: 'lines',
        line: { color: 'rgba(15,118,110,0)' },
        fill: 'tonexty',
        fillcolor: 'rgba(15,118,110,0.16)',
        hoverinfo: 'skip',
        name: '95% confidence interval',
      },
      {
        x: points.map(point => point.year),
        y: points.map(point => point.value),
        type: 'scatter',
        mode: 'lines+markers',
        line: { color: '#0f766e', dash: 'dash', width: 2.5 },
        marker: { color: '#ffffff', line: { color: '#0f766e', width: 2 }, size: 7 },
        name: `${forecast.evaluation.selected_model} · estimate`,
      },
    );
  }

  return (
    <div role="img" aria-label={`${title}. Historical observations use solid lines; estimates use a dashed line and confidence band.`}>
      <Plot
        data={traces}
        layout={{
          title: { text: title, font: { size: 18 } },
          xaxis: { title: { text: 'Year' }, gridcolor: '#e2e8f0' },
          yaxis: { title: { text: yAxisTitle }, gridcolor: '#e2e8f0', zerolinecolor: '#94a3b8' },
          legend: { orientation: 'h', y: -0.2 },
          margin: { t: 55, l: 70, r: 24, b: 90 },
          paper_bgcolor: 'rgba(0,0,0,0)',
          plot_bgcolor: 'rgba(248,250,252,0.75)',
          hovermode: 'x unified',
          autosize: true,
        }}
        style={{ width: '100%', height: '460px' }}
        config={{ responsive: true, displaylogo: false, scrollZoom: false }}
        useResizeHandler
      />
    </div>
  );
}
