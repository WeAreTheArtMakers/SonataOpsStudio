import Link from 'next/link';

const links = [
  { href: '/dashboard', label: 'Open Dashboard' },
  { href: '/anomalies', label: 'Review Anomalies' },
  { href: '/listen', label: 'Generate Soundscape' },
  { href: '/copilot', label: 'Ask Copilot' },
  { href: '/briefs', label: 'Read Briefs' },
  { href: '/admin', label: 'Admin Controls' }
];

export default function HomePage() {
  return (
    <section className="panel overflow-hidden p-8">
      <p className="section-title">Enterprise Product Demo</p>
      <h1 className="mt-2 max-w-3xl text-4xl font-semibold leading-tight">
        Turn KPI time-series into dashboards, soundscapes, and C-level action briefs.
      </h1>
      <p className="mt-4 max-w-2xl text-sand/80">
        SonataOps Studio combines ClickHouse analytics, tenant-aware pgvector RAG, automation flows, and
        audio rendering to reduce dashboard fatigue and speed decision loops.
      </p>

      <div className="mt-8 grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-3">
        {links.map((link) => (
          <Link
            key={link.href}
            href={link.href}
            className="rounded-2xl border border-white/10 bg-white/5 px-4 py-4 text-sm uppercase tracking-[0.14em] text-mint transition hover:bg-white/10"
          >
            {link.label}
          </Link>
        ))}
      </div>
    </section>
  );
}
