import type { IndicatorPoint } from '../types';

interface ExportCSVProps {
  data: IndicatorPoint[];
  fileName: string;
  disabled?: boolean;
}

export default function ExportCSV({
  data,
  fileName,
  disabled = false,
}: ExportCSVProps) {
  const downloadCSV = () => {
    if (data.length === 0) {
      return;
    }

    const headers = Object.keys(data[0]) as Array<keyof IndicatorPoint>;
    const rows = [
      headers.join(','),
      ...data.map(row => (
        headers
          .map(field => JSON.stringify(row[field] ?? ''))
          .join(',')
      )),
    ];

    const csvContent = `\uFEFF${rows.join('\n')}`;
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');

    link.href = url;
    link.download = `${fileName}.csv`;
    document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(url);
  };

  return (
    <button type="button" onClick={downloadCSV} disabled={disabled}>
      Export CSV
    </button>
  );
}
