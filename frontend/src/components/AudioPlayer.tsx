'use client';

interface Props {
  url: string | null;
  label?: string;
}

export default function AudioPlayer({ url, label = 'Generated Audio' }: Props) {
  return (
    <section className="panel p-4">
      <p className="section-title">{label}</p>
      {url ? (
        <div className="mt-3 space-y-3">
          <audio controls className="w-full" src={url} />
          <div className="h-2 overflow-hidden rounded-full bg-white/10">
            <div className="h-full w-2/3 animate-pulse bg-mint/70" />
          </div>
        </div>
      ) : (
        <p className="mt-3 text-sm text-sand/70">No artifact selected yet.</p>
      )}
    </section>
  );
}
