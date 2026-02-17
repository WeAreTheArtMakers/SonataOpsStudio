'use client';

import { FormEvent, useState } from 'react';
import ReactMarkdown from 'react-markdown';

import { askCopilot } from '@/lib/api';
import { SourceItem } from '@/lib/types';

interface Message {
  role: 'user' | 'assistant';
  content: string;
}

interface Props {
  onSources: (sources: SourceItem[]) => void;
}

export default function CopilotChat({ onSources }: Props) {
  const [question, setQuestion] = useState('Explain this anomaly and provide likely causes with citations.');
  const [messages, setMessages] = useState<Message[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const send = async (event?: FormEvent, overrideQuestion?: string) => {
    if (event) {
      event.preventDefault();
    }
    const q = (overrideQuestion || question).trim();
    if (!q) {
      return;
    }

    setError(null);
    setLoading(true);
    setMessages((prev) => [...prev, { role: 'user', content: q }]);

    try {
      const mode = q.toLowerCase().includes('summary') ? 'exec_summary' : q.toLowerCase().includes('next') ? 'next_steps' : 'anomaly_explainer';
      const result = await askCopilot({ question: q, mode });
      setMessages((prev) => [...prev, { role: 'assistant', content: result.answer }]);
      onSources(result.top_sources);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setLoading(false);
      setQuestion('');
    }
  };

  return (
    <section className="panel p-4">
      <p className="section-title">Grounded Copilot</p>
      <div className="mt-3 flex flex-wrap gap-2">
        <button className="rounded-lg bg-white/10 px-3 py-1 text-xs" onClick={() => send(undefined, 'Explain this anomaly with citations')}>
          Explain this anomaly
        </button>
        <button className="rounded-lg bg-white/10 px-3 py-1 text-xs" onClick={() => send(undefined, 'Suggest next steps for mitigation with owners')}>
          Suggest next steps
        </button>
        <button className="rounded-lg bg-white/10 px-3 py-1 text-xs" onClick={() => send(undefined, 'Draft exec summary for today anomalies')}>
          Draft exec summary
        </button>
      </div>

      <div className="mt-4 max-h-[420px] space-y-3 overflow-y-auto rounded-xl border border-white/10 bg-black/10 p-3">
        {messages.length === 0 ? <p className="text-sm text-sand/70">Ask a grounded question to start.</p> : null}
        {messages.map((msg, idx) => (
          <article
            key={`${msg.role}-${idx}`}
            className={`rounded-xl px-3 py-2 text-sm ${msg.role === 'user' ? 'bg-teal/20' : 'bg-white/5'}`}
          >
            <p className="mb-1 text-[11px] uppercase tracking-[0.12em] text-mint/70">{msg.role}</p>
            <div className="prose prose-invert max-w-none text-sm">
              <ReactMarkdown>{msg.content}</ReactMarkdown>
            </div>
          </article>
        ))}
      </div>

      <form onSubmit={send} className="mt-4 space-y-2">
        <textarea
          className="h-24 w-full rounded-xl border border-white/10 bg-white/5 px-3 py-2 text-sm"
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          placeholder="Ask about anomaly drivers, likely causes, and next actions..."
        />
        <button
          type="submit"
          disabled={loading}
          className="rounded-xl bg-mint/80 px-4 py-2 text-xs font-semibold uppercase tracking-[0.14em] text-ink disabled:opacity-60"
        >
          {loading ? 'Thinking...' : 'Send'}
        </button>
      </form>

      {error ? <p className="mt-2 text-sm text-ember">{error}</p> : null}
    </section>
  );
}
