'use client';

import { useMemo, useState } from 'react';

import { getAudioJob, getAudioUrl, queueAudioRender } from '@/lib/api';

const PRESETS = ['Executive Minimal', 'Risk Tension', 'Growth Momentum'];

interface Props {
  initialMetric?: string;
  onReady: (url: string, artifactId: string) => void;
}

function toInputLocal(iso: string): string {
  const date = new Date(iso);
  const offset = date.getTimezoneOffset();
  const adjusted = new Date(date.getTime() - offset * 60 * 1000);
  return adjusted.toISOString().slice(0, 16);
}

function fromInputLocal(localValue: string): string {
  return new Date(localValue).toISOString();
}

export default function SonificationControls({ initialMetric = 'RiskScore', onReady }: Props) {
  const now = useMemo(() => new Date(), []);
  const defaultStart = new Date(now.getTime() - 60 * 60 * 1000).toISOString();

  const [metric, setMetric] = useState(initialMetric);
  const [preset, setPreset] = useState(PRESETS[0]);
  const [duration, setDuration] = useState(20);
  const [start, setStart] = useState(defaultStart);
  const [end, setEnd] = useState(now.toISOString());
  const [status, setStatus] = useState('idle');
  const [error, setError] = useState<string | null>(null);

  const runRender = async () => {
    setError(null);
    setStatus('queueing');

    try {
      const queued = await queueAudioRender({
        metric_name: metric,
        preset,
        duration,
        start,
        end
      });

      setStatus('processing');
      for (let i = 0; i < 80; i += 1) {
        await new Promise((resolve) => setTimeout(resolve, 2000));
        const job = await getAudioJob(queued.job_id);

        if (job.status === 'completed' && job.artifact_id) {
          const urlResp = await getAudioUrl(job.artifact_id, 'mp3');
          onReady(urlResp.url, job.artifact_id);
          setStatus('completed');
          return;
        }

        if (job.status === 'failed') {
          throw new Error(job.error || 'audio render failed');
        }
      }

      throw new Error('timeout while waiting for render completion');
    } catch (err) {
      setStatus('failed');
      setError((err as Error).message);
    }
  };

  return (
    <section className="panel p-4">
      <p className="section-title">Soundscape Controls</p>
      <div className="mt-3 grid grid-cols-1 gap-3 md:grid-cols-2">
        <label className="text-xs uppercase tracking-[0.12em] text-sand/70">
          Metric
          <input
            className="mt-1 w-full rounded-xl border border-white/10 bg-white/5 px-3 py-2 text-sm"
            value={metric}
            onChange={(e) => setMetric(e.target.value)}
          />
        </label>

        <label className="text-xs uppercase tracking-[0.12em] text-sand/70">
          Preset
          <select
            className="mt-1 w-full rounded-xl border border-white/10 bg-white/5 px-3 py-2 text-sm"
            value={preset}
            onChange={(e) => setPreset(e.target.value)}
          >
            {PRESETS.map((item) => (
              <option key={item} value={item}>
                {item}
              </option>
            ))}
          </select>
        </label>

        <label className="text-xs uppercase tracking-[0.12em] text-sand/70">
          Start
          <input
            type="datetime-local"
            className="mt-1 w-full rounded-xl border border-white/10 bg-white/5 px-3 py-2 text-sm"
            value={toInputLocal(start)}
            onChange={(e) => setStart(fromInputLocal(e.target.value))}
          />
        </label>

        <label className="text-xs uppercase tracking-[0.12em] text-sand/70">
          End
          <input
            type="datetime-local"
            className="mt-1 w-full rounded-xl border border-white/10 bg-white/5 px-3 py-2 text-sm"
            value={toInputLocal(end)}
            onChange={(e) => setEnd(fromInputLocal(e.target.value))}
          />
        </label>
      </div>

      <div className="mt-4">
        <label className="text-xs uppercase tracking-[0.12em] text-sand/70">Duration: {duration}s</label>
        <input
          type="range"
          min={5}
          max={120}
          value={duration}
          onChange={(e) => setDuration(Number(e.target.value))}
          className="mt-1 w-full accent-mint"
        />
      </div>

      <div className="mt-4 flex items-center gap-3">
        <button
          onClick={runRender}
          className="rounded-xl bg-mint/80 px-4 py-2 text-xs font-semibold uppercase tracking-[0.14em] text-ink"
        >
          Generate
        </button>
        <span className="text-xs uppercase tracking-[0.12em] text-sand/70">Status: {status}</span>
      </div>
      {error ? <p className="mt-3 text-sm text-ember">{error}</p> : null}
    </section>
  );
}
