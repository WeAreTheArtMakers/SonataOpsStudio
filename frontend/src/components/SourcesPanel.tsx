import { SourceItem } from '@/lib/types';

interface Props {
  sources: SourceItem[];
}

export default function SourcesPanel({ sources }: Props) {
  return (
    <aside className="panel h-full p-4">
      <p className="section-title">Sources</p>
      <div className="mt-3 space-y-3">
        {sources.length === 0 ? <p className="text-sm text-sand/70">No sources loaded yet.</p> : null}
        {sources.map((source) => (
          <article key={source.id} className="rounded-xl border border-white/10 bg-white/5 p-3 text-xs">
            <p className="font-semibold text-mint">[{source.id}] {source.title}</p>
            <p className="mt-1 whitespace-pre-wrap text-sand/85">{source.snippet}</p>
            {source.url ? (
              <a className="mt-2 inline-block text-teal-200 underline" href={source.url} target="_blank">
                {source.url}
              </a>
            ) : null}
          </article>
        ))}
      </div>
    </aside>
  );
}
