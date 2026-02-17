'use client';

import { useEffect, useMemo, useState } from 'react';

import KpiCards from '@/components/KpiCards';
import TimeseriesChart from '@/components/TimeseriesChart';
import { getAdminStatus, getAnomalyAnalytics, getAudioAnalytics, getKpiAnalytics } from '@/lib/api';
import { subscribeEvents } from '@/lib/ws';

type DashboardState = {
  anomaliesToday: number;
  p95Severity: number;
  audioRenders: number;
  ragQueries: number;
};

export default function DashboardPage() {
  const [kpiRows, setKpiRows] = useState<Array<{ bucket: string; avg: number; min: number; max: number }>>([]);
  const [anomalyCounts, setAnomalyCounts] = useState<Array<{ bucket: string; count: number }>>([]);
  const [severityRows, setSeverityRows] = useState<Array<{ bucket: string; p95: number }>>([]);
  const [cards, setCards] = useState<DashboardState>({
    anomaliesToday: 0,
    p95Severity: 0,
    audioRenders: 0,
    ragQueries: 0
  });
  const [events, setEvents] = useState<string[]>([]);

  useEffect(() => {
    const load = async () => {
      const [admin, kpi, anomaly, audio] = await Promise.all([
        getAdminStatus(),
        getKpiAnalytics('Sales', 360),
        getAnomalyAnalytics(1440),
        getAudioAnalytics(1440)
      ]);

      const groupedCounts = anomaly.counts.reduce<Record<string, number>>((acc, row) => {
        acc[row.bucket] = (acc[row.bucket] || 0) + row.count;
        return acc;
      }, {});

      setKpiRows(kpi.rows.map((row) => ({ bucket: row.bucket.slice(11, 16), avg: row.avg, min: row.min, max: row.max })));
      setAnomalyCounts(
        Object.entries(groupedCounts)
          .sort(([a], [b]) => a.localeCompare(b))
          .map(([bucket, count]) => ({ bucket: bucket.slice(11, 16), count }))
      );
      setSeverityRows(
        anomaly.severity_p95
          .sort((a, b) => a.bucket.localeCompare(b.bucket))
          .map((row) => ({ bucket: row.bucket.slice(11, 16), p95: row.p95 }))
      );

      const totalAudio = audio.rows.reduce((sum, row) => sum + row.renders, 0);
      const latestP95 = anomaly.severity_p95.at(-1)?.p95 || 0;
      setCards({
        anomaliesToday: admin.anomalies,
        p95Severity: Math.round(latestP95),
        audioRenders: totalAudio,
        ragQueries: admin.rag_queries
      });
    };

    load().catch((error) => {
      setEvents((prev) => [`load error: ${(error as Error).message}`, ...prev].slice(0, 8));
    });

    const unsubscribe = subscribeEvents((event) => {
      setEvents((prev) => [`${event.type} @ ${new Date(event.created_at).toLocaleTimeString()}`, ...prev].slice(0, 8));
    });

    return unsubscribe;
  }, []);

  const severityDistribution = useMemo(
    () => severityRows.map((row) => ({ bucket: row.bucket, p95: row.p95 })),
    [severityRows]
  );

  return (
    <div className="space-y-4">
      <KpiCards {...cards} />

      <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
        <TimeseriesChart
          title="Sales KPI Trend"
          data={kpiRows}
          lines={[
            { key: 'avg', color: '#8dd8c7', label: 'Avg' },
            { key: 'max', color: '#e07a5f', label: 'Max' },
            { key: 'min', color: '#6ec1e4', label: 'Min' }
          ]}
        />

        <TimeseriesChart
          title="Anomaly Rate"
          data={anomalyCounts}
          lines={[{ key: 'count', color: '#e07a5f', label: 'Count' }]}
        />
      </div>

      <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
        <TimeseriesChart
          title="Severity P95"
          data={severityDistribution}
          lines={[{ key: 'p95', color: '#f2e8cf', label: 'P95 Severity' }]}
        />

        <section className="panel p-4">
          <p className="section-title">Realtime Pipeline Events</p>
          <div className="mt-3 space-y-2 text-sm">
            {events.length === 0 ? <p className="text-sand/70">Waiting for events...</p> : null}
            {events.map((item, idx) => (
              <p key={`${item}-${idx}`} className="rounded-lg border border-white/10 bg-white/5 px-3 py-2">
                {item}
              </p>
            ))}
          </div>
        </section>
      </div>
    </div>
  );
}
