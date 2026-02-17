'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';

import AnomalyDetailDrawer from '@/components/AnomalyDetailDrawer';
import AnomalyTable from '@/components/AnomalyTable';
import { askCopilot, getAnomalies } from '@/lib/api';
import { Anomaly } from '@/lib/types';

export default function AnomaliesPage() {
  const router = useRouter();
  const [metricFilter, setMetricFilter] = useState('');
  const [anomalies, setAnomalies] = useState<Anomaly[]>([]);
  const [selected, setSelected] = useState<Anomaly | null>(null);
  const [explanation, setExplanation] = useState<string>('');
  const [loading, setLoading] = useState(false);

  const load = async () => {
    const res = await getAnomalies(metricFilter || undefined);
    setAnomalies(res.items);
  };

  useEffect(() => {
    load().catch(() => setAnomalies([]));
  }, [metricFilter]);

  const explain = async (item: Anomaly) => {
    setLoading(true);
    try {
      const result = await askCopilot({
        question: `Explain anomaly ${item.anomaly_id} for metric ${item.metric_name} with impact and next steps`,
        context: { anomaly_id: item.anomaly_id, metric: item.metric_name }
      });
      setExplanation(result.answer);
    } finally {
      setLoading(false);
    }
  };

  const generate = (item: Anomaly) => {
    router.push(`/listen?metric=${encodeURIComponent(item.metric_name)}&anomaly=${item.anomaly_id}`);
  };

  return (
    <div className="space-y-4">
      <section className="panel p-4">
        <p className="section-title">Anomaly Feed</p>
        <div className="mt-3 flex items-center gap-2">
          <input
            value={metricFilter}
            onChange={(e) => setMetricFilter(e.target.value)}
            placeholder="Filter by metric (e.g. RiskScore)"
            className="w-full max-w-sm rounded-xl border border-white/10 bg-white/5 px-3 py-2 text-sm"
          />
          <button className="rounded-xl bg-white/10 px-3 py-2 text-xs uppercase" onClick={() => load()}>
            Refresh
          </button>
        </div>
      </section>

      <AnomalyTable anomalies={anomalies} onSelect={setSelected} />

      <section className="panel p-4">
        <p className="section-title">Copilot Explanation</p>
        {loading ? <p className="mt-3 text-sm text-sand/70">Generating explanation...</p> : null}
        {explanation ? <pre className="mt-3 whitespace-pre-wrap text-sm text-sand/90">{explanation}</pre> : <p className="mt-3 text-sm text-sand/70">Select an anomaly and click Explain.</p>}
      </section>

      <AnomalyDetailDrawer
        anomaly={selected}
        onClose={() => setSelected(null)}
        onExplain={(item) => explain(item).catch(() => setExplanation('Explanation failed'))}
        onGenerateSound={generate}
      />
    </div>
  );
}
