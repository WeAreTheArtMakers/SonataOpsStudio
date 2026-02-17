export function fmtNumber(value: number, digits = 1): string {
  return new Intl.NumberFormat('en-US', { maximumFractionDigits: digits }).format(value);
}

export function fmtPercent(value: number): string {
  return `${(value * 100).toFixed(1)}%`;
}

export function fmtDateTime(iso: string): string {
  return new Date(iso).toLocaleString();
}

export function severityTone(value: number): string {
  if (value >= 80) return 'text-ember';
  if (value >= 60) return 'text-yellow-300';
  if (value >= 40) return 'text-mint';
  return 'text-sand';
}
