import type { IndicatorPoint } from '../types';
import { safeCsvFileName, serializeIndicatorCsv } from '../csv';

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

    const csvContent = serializeIndicatorCsv(data);
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');

    link.href = url;
    link.download = `${safeCsvFileName(fileName)}.csv`;
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
