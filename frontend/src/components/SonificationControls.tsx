'use client';

import { useMemo, useState } from 'react';

import { getAudioJob, getAudioUrl, queueAudioRender } from '@/lib/api';

const PRESET_DEFAULTS: Record<
  string,
  {
    description: string;
    tempo_min: number;
    tempo_max: number;
    intensity: number;
    glitch_density: number;
    harmonizer_mix: number;
    pad_depth: number;
    ambient_mix: number;
  }
> = {
  'Executive Minimal': {
    description: 'Clean, restrained, boardroom-safe tones.',
    tempo_min: 60,
    tempo_max: 132,
    intensity: 0.45,
    glitch_density: 0.08,
    harmonizer_mix: 0.3,
    pad_depth: 0.58,
    ambient_mix: 0.36
  },
  'Risk Tension': {
    description: 'Minor harmonic pressure with sharper transients.',
    tempo_min: 68,
    tempo_max: 145,
    intensity: 0.66,
    glitch_density: 0.42,
    harmonizer_mix: 0.48,
    pad_depth: 0.52,
    ambient_mix: 0.4
  },
  'Growth Momentum': {
    description: 'Forward major feel with reliable pulse.',
    tempo_min: 72,
    tempo_max: 150,
    intensity: 0.56,
    glitch_density: 0.18,
    harmonizer_mix: 0.52,
    pad_depth: 0.62,
    ambient_mix: 0.46
  },
  'State Azure': {
    description: 'Ambient corporate pad with rich harmonizer lift.',
    tempo_min: 56,
    tempo_max: 126,
    intensity: 0.54,
    glitch_density: 0.22,
    harmonizer_mix: 0.66,
    pad_depth: 0.9,
    ambient_mix: 0.86
  },
  'Glitch Harmonics': {
    description: 'High-detail glitch texture with layered harmonics.',
    tempo_min: 82,
    tempo_max: 158,
    intensity: 0.82,
    glitch_density: 0.76,
    harmonizer_mix: 0.74,
    pad_depth: 0.46,
    ambient_mix: 0.4
  },
  'Ambient Boardroom': {
    description: 'Low-fatigue cinematic bed for executive briefings.',
    tempo_min: 52,
    tempo_max: 118,
    intensity: 0.36,
    glitch_density: 0.05,
    harmonizer_mix: 0.56,
    pad_depth: 0.94,
    ambient_mix: 0.8
  }
};

const PRESETS = Object.keys(PRESET_DEFAULTS);

type ControlsState = Omit<(typeof PRESET_DEFAULTS)[string], 'description'>;

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
  const initialPreset = PRESETS[0];

  const [metric, setMetric] = useState(initialMetric);
  const [preset, setPreset] = useState(initialPreset);
  const [duration, setDuration] = useState(20);
  const [start, setStart] = useState(defaultStart);
  const [end, setEnd] = useState(now.toISOString());
  const [controls, setControls] = useState<ControlsState>({
    tempo_min: PRESET_DEFAULTS[initialPreset].tempo_min,
    tempo_max: PRESET_DEFAULTS[initialPreset].tempo_max,
    intensity: PRESET_DEFAULTS[initialPreset].intensity,
    glitch_density: PRESET_DEFAULTS[initialPreset].glitch_density,
    harmonizer_mix: PRESET_DEFAULTS[initialPreset].harmonizer_mix,
    pad_depth: PRESET_DEFAULTS[initialPreset].pad_depth,
    ambient_mix: PRESET_DEFAULTS[initialPreset].ambient_mix
  });
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
        end,
        controls
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

  const applyPresetDefaults = (name: string) => {
    const defaults = PRESET_DEFAULTS[name];
    setPreset(name);
    setControls({
      tempo_min: defaults.tempo_min,
      tempo_max: defaults.tempo_max,
      intensity: defaults.intensity,
      glitch_density: defaults.glitch_density,
      harmonizer_mix: defaults.harmonizer_mix,
      pad_depth: defaults.pad_depth,
      ambient_mix: defaults.ambient_mix
    });
  };

  return (
    <section className="panel p-4">
      <p className="section-title">Soundscape Controls</p>
      <p className="mt-2 text-xs text-sand/70">{PRESET_DEFAULTS[preset].description}</p>
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
            onChange={(e) => applyPresetDefaults(e.target.value)}
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

      <div className="mt-4 grid grid-cols-1 gap-3 md:grid-cols-2">
        <label className="text-xs uppercase tracking-[0.12em] text-sand/70">
          Tempo Floor: {controls.tempo_min} BPM
          <input
            type="range"
            min={50}
            max={160}
            value={controls.tempo_min}
            onChange={(e) => {
              const value = Number(e.target.value);
              setControls((prev) => ({
                ...prev,
                tempo_min: value,
                tempo_max: Math.max(prev.tempo_max, value + 5)
              }));
            }}
            className="mt-1 w-full accent-mint"
          />
        </label>

        <label className="text-xs uppercase tracking-[0.12em] text-sand/70">
          Tempo Ceiling: {controls.tempo_max} BPM
          <input
            type="range"
            min={60}
            max={180}
            value={controls.tempo_max}
            onChange={(e) => {
              const value = Number(e.target.value);
              setControls((prev) => ({
                ...prev,
                tempo_min: Math.min(prev.tempo_min, value - 5),
                tempo_max: value
              }));
            }}
            className="mt-1 w-full accent-mint"
          />
        </label>

        <label className="text-xs uppercase tracking-[0.12em] text-sand/70">
          Intensity: {controls.intensity.toFixed(2)}
          <input
            type="range"
            min={0.1}
            max={1}
            step={0.01}
            value={controls.intensity}
            onChange={(e) => setControls((prev) => ({ ...prev, intensity: Number(e.target.value) }))}
            className="mt-1 w-full accent-mint"
          />
        </label>

        <label className="text-xs uppercase tracking-[0.12em] text-sand/70">
          Glitch Texture: {controls.glitch_density.toFixed(2)}
          <input
            type="range"
            min={0}
            max={1}
            step={0.01}
            value={controls.glitch_density}
            onChange={(e) => setControls((prev) => ({ ...prev, glitch_density: Number(e.target.value) }))}
            className="mt-1 w-full accent-mint"
          />
        </label>

        <label className="text-xs uppercase tracking-[0.12em] text-sand/70">
          Harmonizer Mix: {controls.harmonizer_mix.toFixed(2)}
          <input
            type="range"
            min={0}
            max={1}
            step={0.01}
            value={controls.harmonizer_mix}
            onChange={(e) => setControls((prev) => ({ ...prev, harmonizer_mix: Number(e.target.value) }))}
            className="mt-1 w-full accent-mint"
          />
        </label>

        <label className="text-xs uppercase tracking-[0.12em] text-sand/70">
          Pad Depth: {controls.pad_depth.toFixed(2)}
          <input
            type="range"
            min={0.1}
            max={1}
            step={0.01}
            value={controls.pad_depth}
            onChange={(e) => setControls((prev) => ({ ...prev, pad_depth: Number(e.target.value) }))}
            className="mt-1 w-full accent-mint"
          />
        </label>

        <label className="text-xs uppercase tracking-[0.12em] text-sand/70">
          Ambient Wash: {controls.ambient_mix.toFixed(2)}
          <input
            type="range"
            min={0}
            max={1}
            step={0.01}
            value={controls.ambient_mix}
            onChange={(e) => setControls((prev) => ({ ...prev, ambient_mix: Number(e.target.value) }))}
            className="mt-1 w-full accent-mint"
          />
        </label>
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
