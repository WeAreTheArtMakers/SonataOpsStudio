'use client';

import { Anomaly } from '@/lib/types';
import { fmtDateTime, severityTone } from '@/lib/format';

interface Props {
  anomaly: Anomaly | null;
  onClose: () => void;
  onExplain: (anomaly: Anomaly) => void;
  onGenerateSound: (anomaly: Anomaly) => void;
}

export default function AnomalyDetailDrawer({ anomaly, onClose, onExplain, onGenerateSound }: Props) {
  return (
    <aside
      className={`fixed right-0 top-0 z-50 h-full w-full max-w-md transform border-l border-white/15 bg-ink/95 p-5 backdrop-blur-xl transition-transform duration-300 ${
        anomaly ? 'translate-x-0' : 'translate-x-full'
      }`}
    >
      <button className="rounded-lg bg-white/10 px-3 py-1 text-xs uppercase" onClick={onClose}>
        Close
      </button>
      {anomaly ? (
        <div className="mt-4 space-y-4">
          <div>
            <p className="section-title">Anomaly Detail</p>
            <h3 className="mt-1 text-xl font-semibold">{anomaly.metric_name}</h3>
            <p className={`text-sm ${severityTone(anomaly.severity)}`}>Severity {anomaly.severity}</p>
            <p className="text-xs text-sand/70">Detected {fmtDateTime(anomaly.detected_at)}</p>
          </div>

          <div className="panel p-3 text-xs">
            <p>Window Start: {fmtDateTime(anomaly.window_start)}</p>
            <p>Window End: {fmtDateTime(anomaly.window_end)}</p>
            <p>Trend: {Number(anomaly.features?.trend || 0).toFixed(3)}</p>
            <p>Volatility: {Number(anomaly.features?.volatility || 0).toFixed(3)}</p>
            <p>Residual z: {Number(anomaly.features?.residual || 0).toFixed(3)}</p>
            <p>Change point: {Number(anomaly.features?.change_point || 0).toFixed(3)}</p>
          </div>

          <div className="flex flex-wrap gap-2">
            <button
              className="rounded-xl bg-teal/70 px-3 py-2 text-xs font-semibold uppercase tracking-[0.14em]"
              onClick={() => onExplain(anomaly)}
            >
              Explain
            </button>
            <button
              className="rounded-xl bg-mint/70 px-3 py-2 text-xs font-semibold uppercase tracking-[0.14em] text-ink"
              onClick={() => onGenerateSound(anomaly)}
            >
              Generate Sound
            </button>
          </div>
        </div>
      ) : null}
    </aside>
  );
}
