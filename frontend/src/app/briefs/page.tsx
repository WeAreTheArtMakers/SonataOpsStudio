'use client';

import { useEffect, useState } from 'react';

import BriefComposer from '@/components/BriefComposer';
import { API_BASE, createBrief, getBriefs, triggerExecBrief } from '@/lib/api';
import { Brief } from '@/lib/types';

export default function BriefsPage() {
  const [briefs, setBriefs] = useState<Brief[]>([]);
  const [status, setStatus] = useState<string>('');

  const load = async () => {
    const result = await getBriefs();
    setBriefs(result.items);
  };

  useEffect(() => {
    load().catch(() => setBriefs([]));
  }, []);

  const onCreate = async (title: string, body: string) => {
    await createBrief({ title, body_md: body, data: { source: 'manual' } });
    setStatus('brief saved');
    await load();
  };

  const runAutomation = async () => {
    await triggerExecBrief();
    setStatus('exec brief flow triggered');
  };

  return (
    <div className="space-y-4">
      <section className="panel p-4">
        <p className="section-title">Executive Briefing</p>
        <div className="mt-3 flex gap-2">
          <button
            className="rounded-xl bg-teal/70 px-3 py-2 text-xs uppercase tracking-[0.14em]"
            onClick={() => runAutomation().catch(() => setStatus('trigger failed'))}
          >
            Trigger n8n Brief Flow
          </button>
          {status ? <p className="text-sm text-sand/80">{status}</p> : null}
        </div>
      </section>

      <BriefComposer briefs={briefs} onCreate={onCreate} apiBase={API_BASE} />
    </div>
  );
}
