import { Anomaly } from '@/lib/types';
import { fmtDateTime, severityTone } from '@/lib/format';

interface Props {
  anomalies: Anomaly[];
  onSelect: (item: Anomaly) => void;
}

export default function AnomalyTable({ anomalies, onSelect }: Props) {
  return (
    <div className="panel overflow-hidden">
      <div className="overflow-x-auto">
        <table className="min-w-full text-left text-sm">
          <thead className="bg-white/5 text-xs uppercase tracking-[0.14em] text-mint/80">
            <tr>
              <th className="px-4 py-3">Metric</th>
              <th className="px-4 py-3">Severity</th>
              <th className="px-4 py-3">Window End</th>
              <th className="px-4 py-3">Trend</th>
              <th className="px-4 py-3">Volatility</th>
            </tr>
          </thead>
          <tbody>
            {anomalies.map((item) => (
              <tr
                key={item.anomaly_id}
                onClick={() => onSelect(item)}
                className="cursor-pointer border-t border-white/10 hover:bg-white/5"
              >
                <td className="px-4 py-3">{item.metric_name}</td>
                <td className={`px-4 py-3 font-semibold ${severityTone(item.severity)}`}>{item.severity}</td>
                <td className="px-4 py-3 text-sand/75">{fmtDateTime(item.window_end)}</td>
                <td className="px-4 py-3">{Number(item.features?.trend || 0).toFixed(2)}</td>
                <td className="px-4 py-3">{Number(item.features?.volatility || 0).toFixed(2)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
