'use client';

import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis
} from 'recharts';

interface SeriesRow {
  bucket: string;
  [key: string]: string | number;
}

interface Props {
  title: string;
  data: SeriesRow[];
  lines: Array<{ key: string; color: string; label?: string }>;
}

export default function TimeseriesChart({ title, data, lines }: Props) {
  return (
    <section className="panel p-4">
      <p className="section-title">{title}</p>
      <div className="mt-3 h-72 w-full">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data}>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.12)" />
            <XAxis dataKey="bucket" tick={{ fill: '#d9d2be', fontSize: 11 }} tickMargin={8} minTickGap={20} />
            <YAxis tick={{ fill: '#d9d2be', fontSize: 11 }} />
            <Tooltip contentStyle={{ background: '#0f1d2d', border: '1px solid rgba(255,255,255,0.15)' }} />
            <Legend />
            {lines.map((line) => (
              <Line
                key={line.key}
                type="monotone"
                dataKey={line.key}
                stroke={line.color}
                strokeWidth={2}
                dot={false}
                name={line.label || line.key}
              />
            ))}
          </LineChart>
        </ResponsiveContainer>
      </div>
    </section>
  );
}
