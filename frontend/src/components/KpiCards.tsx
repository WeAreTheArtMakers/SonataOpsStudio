import { fmtNumber } from '@/lib/format';

interface Props {
  anomaliesToday: number;
  p95Severity: number;
  audioRenders: number;
  ragQueries: number;
}

export default function KpiCards(props: Props) {
  const cards = [
    { label: 'Anomalies Today', value: props.anomaliesToday, accent: 'text-ember' },
    { label: 'P95 Severity', value: props.p95Severity, accent: 'text-yellow-300' },
    { label: 'Audio Renders', value: props.audioRenders, accent: 'text-mint' },
    { label: 'RAG Queries', value: props.ragQueries, accent: 'text-teal-300' }
  ];

  return (
    <section className="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-4">
      {cards.map((card) => (
        <article key={card.label} className="kpi-card">
          <p className="section-title">{card.label}</p>
          <p className={`mt-2 text-3xl font-semibold ${card.accent}`}>{fmtNumber(card.value, 0)}</p>
        </article>
      ))}
    </section>
  );
}
