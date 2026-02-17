'use client';

import { useEffect, useState } from 'react';

import EvalDashboard from '@/components/EvalDashboard';
import {
  approvePrompt,
  getAdminStatus,
  getEvalResults,
  getPromptApprovals,
  getHealth,
  ingestDocs,
  runEval,
  seedDemo
} from '@/lib/api';
import { EvalResult } from '@/lib/types';

export default function AdminPage() {
  const [health, setHealth] = useState<{ status: string; postgres: boolean; clickhouse: boolean; minio: boolean } | null>(null);
  const [status, setStatus] = useState<{ anomalies: number; briefs: number; rag_queries: number } | null>(null);
  const [evalPassRate, setEvalPassRate] = useState(0);
  const [evalItems, setEvalItems] = useState<EvalResult[]>([]);
  const [promptRequests, setPromptRequests] = useState<Array<{ request_id: string; status: string; prompt_preview: string }>>([]);
  const [docTitle, setDocTitle] = useState('Incident Note - CDN Saturation');
  const [docText, setDocText] = useState('A high-traffic campaign window caused CDN cache churn and latency spikes for 18 minutes. Mitigation included edge pool scaling and cache warm-up.');
  const [notice, setNotice] = useState('');

  const loadAll = async () => {
    const [h, s, e, p] = await Promise.all([getHealth(), getAdminStatus(), getEvalResults(), getPromptApprovals()]);
    setHealth(h);
    setStatus({ anomalies: s.anomalies, briefs: s.briefs, rag_queries: s.rag_queries });
    setEvalPassRate(e.overall_pass_rate || 0);
    setEvalItems(e.items || []);
    setPromptRequests(p.items.map((item) => ({ request_id: item.request_id, status: item.status, prompt_preview: item.prompt_preview })));
  };

  useEffect(() => {
    loadAll().catch(() => setNotice('failed to load admin status'));
  }, []);

  const onSeed = async () => {
    const result = await seedDemo();
    setNotice(`seeded ${result.seeded_points} points and ${result.rag_chunks} chunks`);
    await loadAll();
  };

  const onIngestDoc = async () => {
    const result = await ingestDocs([
      {
        title: docTitle,
        text: docText,
        source_url: 'internal://manual/admin-ingest',
        metadata: { source: 'admin-ui' }
      }
    ]);
    setNotice(`ingested ${result.docs} doc(s), ${result.chunks_inserted} chunks`);
    await loadAll();
  };

  const onRunEval = async () => {
    const result = await runEval(5);
    setNotice(`eval run ${result.run_id} pass rate ${(result.overall_pass_rate * 100).toFixed(1)}%`);
    await loadAll();
  };

  const onApprove = async (requestId: string) => {
    await approvePrompt(requestId);
    setNotice(`approved request ${requestId}`);
    await loadAll();
  };

  return (
    <div className="space-y-4">
      <section className="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-4">
        <article className="kpi-card">
          <p className="section-title">Health</p>
          <p className="mt-2 text-2xl font-semibold">{health?.status || '...'}</p>
        </article>
        <article className="kpi-card">
          <p className="section-title">Anomalies</p>
          <p className="mt-2 text-2xl font-semibold">{status?.anomalies ?? 0}</p>
        </article>
        <article className="kpi-card">
          <p className="section-title">Briefs</p>
          <p className="mt-2 text-2xl font-semibold">{status?.briefs ?? 0}</p>
        </article>
        <article className="kpi-card">
          <p className="section-title">RAG Queries</p>
          <p className="mt-2 text-2xl font-semibold">{status?.rag_queries ?? 0}</p>
        </article>
      </section>

      <section className="panel p-4">
        <p className="section-title">Admin Actions</p>
        <div className="mt-3 flex flex-wrap gap-2">
          <button className="rounded-xl bg-mint/80 px-3 py-2 text-xs uppercase tracking-[0.14em] text-ink" onClick={() => onSeed().catch(() => setNotice('seed failed'))}>
            Seed Demo Data
          </button>
          <button className="rounded-xl bg-teal/70 px-3 py-2 text-xs uppercase tracking-[0.14em]" onClick={() => onRunEval().catch(() => setNotice('eval failed'))}>
            Run Eval
          </button>
          <button className="rounded-xl bg-white/10 px-3 py-2 text-xs uppercase tracking-[0.14em]" onClick={() => loadAll().catch(() => setNotice('reload failed'))}>
            Refresh
          </button>
        </div>
        {notice ? <p className="mt-3 text-sm text-sand/80">{notice}</p> : null}
      </section>

      <section className="grid grid-cols-1 gap-4 xl:grid-cols-2">
        <article className="panel p-4">
          <p className="section-title">Ingest Document</p>
          <div className="mt-3 space-y-2">
            <input
              className="w-full rounded-xl border border-white/10 bg-white/5 px-3 py-2 text-sm"
              value={docTitle}
              onChange={(e) => setDocTitle(e.target.value)}
            />
            <textarea
              className="h-32 w-full rounded-xl border border-white/10 bg-white/5 px-3 py-2 text-sm"
              value={docText}
              onChange={(e) => setDocText(e.target.value)}
            />
            <button className="rounded-xl bg-mint/70 px-3 py-2 text-xs uppercase tracking-[0.14em] text-ink" onClick={() => onIngestDoc().catch(() => setNotice('doc ingest failed'))}>
              Ingest to RAG
            </button>
          </div>
        </article>

        <article className="panel p-4">
          <p className="section-title">Prompt Approval Queue</p>
          <div className="mt-3 space-y-2 text-xs">
            {promptRequests.length === 0 ? <p className="text-sand/70">No pending requests.</p> : null}
            {promptRequests.map((item) => (
              <div key={item.request_id} className="rounded-lg border border-white/10 bg-white/5 p-3">
                <p className="font-semibold">{item.request_id}</p>
                <p className="mt-1 text-sand/70">{item.prompt_preview.slice(0, 120)}...</p>
                {item.status !== 'approved' ? (
                  <button className="mt-2 rounded-lg bg-teal/70 px-2 py-1 uppercase tracking-[0.12em]" onClick={() => onApprove(item.request_id).catch(() => setNotice('approval failed'))}>
                    Approve
                  </button>
                ) : (
                  <p className="mt-1 text-mint">Approved</p>
                )}
              </div>
            ))}
          </div>
        </article>
      </section>

      <EvalDashboard passRate={evalPassRate} items={evalItems} />
    </div>
  );
}
