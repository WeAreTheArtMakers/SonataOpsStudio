'use client';

import { useMemo, useState } from 'react';
import ReactMarkdown from 'react-markdown';

import { Brief } from '@/lib/types';

interface Props {
  briefs: Brief[];
  onCreate: (title: string, body: string) => Promise<void>;
  apiBase: string;
}

export default function BriefComposer({ briefs, onCreate, apiBase }: Props) {
  const [title, setTitle] = useState('Weekly Executive Brief');
  const [body, setBody] = useState('## Topline\n- KPI health stable\n\n## Risks\n- Elevated latency windows in NA\n\n## Decisions\n- Increase autoscaling floor by 12%');
  const [selectedId, setSelectedId] = useState<string | null>(briefs[0]?.brief_id || null);

  const selected = useMemo(
    () => briefs.find((brief) => brief.brief_id === selectedId) || briefs[0] || null,
    [briefs, selectedId]
  );

  return (
    <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
      <section className="panel p-4">
        <p className="section-title">Compose Brief</p>
        <div className="mt-3 space-y-3">
          <input
            className="w-full rounded-xl border border-white/10 bg-white/5 px-3 py-2 text-sm"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
          />
          <textarea
            className="h-56 w-full rounded-xl border border-white/10 bg-white/5 px-3 py-2 text-sm"
            value={body}
            onChange={(e) => setBody(e.target.value)}
          />
          <button
            className="rounded-xl bg-mint/80 px-4 py-2 text-xs font-semibold uppercase tracking-[0.14em] text-ink"
            onClick={() => onCreate(title, body)}
          >
            Save Brief
          </button>
        </div>
      </section>

      <section className="panel p-4">
        <p className="section-title">Brief Library</p>
        <div className="mt-3 grid grid-cols-1 gap-2">
          {briefs.map((brief) => (
            <button
              key={brief.brief_id}
              className={`rounded-lg border px-3 py-2 text-left text-xs ${
                selected?.brief_id === brief.brief_id
                  ? 'border-mint/80 bg-mint/15'
                  : 'border-white/10 bg-white/5'
              }`}
              onClick={() => setSelectedId(brief.brief_id)}
            >
              <p className="font-semibold text-sand">{brief.title}</p>
              <p className="text-sand/60">{new Date(brief.created_at).toLocaleString()}</p>
            </button>
          ))}
        </div>

        {selected ? (
          <article className="prose prose-invert mt-4 max-h-72 overflow-y-auto rounded-xl border border-white/10 bg-black/10 p-3 text-sm">
            <ReactMarkdown>{selected.body_md}</ReactMarkdown>
            <a
              className="mt-3 inline-block text-teal-200 underline"
              href={`${apiBase}/briefs/${selected.brief_id}/export?workspace_id=demo-workspace`}
              target="_blank"
            >
              Export Markdown
            </a>
          </article>
        ) : (
          <p className="mt-3 text-sm text-sand/70">No briefs available.</p>
        )}
      </section>
    </div>
  );
}
