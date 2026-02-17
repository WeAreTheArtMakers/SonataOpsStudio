import { EvalResult } from '@/lib/types';
import { fmtPercent } from '@/lib/format';

interface Props {
  passRate: number;
  items: EvalResult[];
}

export default function EvalDashboard({ passRate, items }: Props) {
  const failures = items.filter((item) => !item.grounded_pass || !item.safety_pass);

  return (
    <section className="panel p-4">
      <p className="section-title">PromptOps Eval</p>
      <div className="mt-3 grid grid-cols-1 gap-3 md:grid-cols-3">
        <article className="rounded-xl bg-white/5 p-3">
          <p className="text-xs uppercase tracking-[0.12em] text-sand/70">Pass Rate</p>
          <p className="mt-1 text-2xl font-semibold text-mint">{fmtPercent(passRate || 0)}</p>
        </article>
        <article className="rounded-xl bg-white/5 p-3">
          <p className="text-xs uppercase tracking-[0.12em] text-sand/70">Cases</p>
          <p className="mt-1 text-2xl font-semibold">{items.length}</p>
        </article>
        <article className="rounded-xl bg-white/5 p-3">
          <p className="text-xs uppercase tracking-[0.12em] text-sand/70">Failures</p>
          <p className="mt-1 text-2xl font-semibold text-ember">{failures.length}</p>
        </article>
      </div>

      <div className="mt-4 space-y-2">
        {failures.slice(0, 5).map((item) => (
          <article key={item.case_id} className="rounded-lg border border-ember/30 bg-ember/10 p-3 text-xs">
            <p className="font-semibold">Case {item.case_id}</p>
            <p className="mt-1 text-sand/85">{item.question}</p>
            <p className="mt-1 text-sand/70">{item.notes}</p>
          </article>
        ))}
        {failures.length === 0 ? <p className="text-sm text-mint">No failures in latest run.</p> : null}
      </div>
    </section>
  );
}
