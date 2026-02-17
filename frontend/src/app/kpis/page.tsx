'use client';

import { useEffect, useState } from 'react';

import TimeseriesChart from '@/components/TimeseriesChart';
import { getKpiAnalytics } from '@/lib/api';

const METRICS = ['Sales', 'RiskScore', 'Traffic', 'Latency'];

export default function KpisPage() {
  const [metric, setMetric] = useState('Sales');
  const [rows, setRows] = useState<Array<{ bucket: string; avg: number; min: number; max: number }>>([]);

  useEffect(() => {
    getKpiAnalytics(metric, 360)
      .then((result) => {
        setRows(result.rows.map((row) => ({ bucket: row.bucket.slice(11, 16), avg: row.avg, min: row.min, max: row.max })));
      })
      .catch(() => setRows([]));
  }, [metric]);

  return (
    <div className="space-y-4">
      <section className="panel p-4">
        <p className="section-title">KPI Explorer</p>
        <div className="mt-3 flex flex-wrap gap-2">
          {METRICS.map((item) => (
            <button
              key={item}
              onClick={() => setMetric(item)}
              className={`rounded-xl px-3 py-2 text-xs uppercase tracking-[0.14em] ${
                metric === item ? 'bg-mint/70 text-ink' : 'bg-white/5 text-sand'
              }`}
            >
              {item}
            </button>
          ))}
        </div>
      </section>

      <TimeseriesChart
        title={`${metric} (1m Rollup)`}
        data={rows}
        lines={[
          { key: 'avg', color: '#8dd8c7', label: 'Average' },
          { key: 'max', color: '#e07a5f', label: 'Max' },
          { key: 'min', color: '#6ec1e4', label: 'Min' }
        ]}
      />
    </div>
  );
}
