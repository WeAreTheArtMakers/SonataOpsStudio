'use client';

import { Suspense, useMemo, useState } from 'react';
import { useSearchParams } from 'next/navigation';

import AudioPlayer from '@/components/AudioPlayer';
import SonificationControls from '@/components/SonificationControls';

export default function ListenPage() {
  return (
    <Suspense fallback={<div className="panel p-4 text-sm text-sand/80">Loading Listen...</div>}>
      <ListenContent />
    </Suspense>
  );
}

function ListenContent() {
  const params = useSearchParams();
  const initialMetric = useMemo(() => params.get('metric') || 'RiskScore', [params]);

  const [url, setUrl] = useState<string | null>(null);
  const [artifactId, setArtifactId] = useState<string | null>(null);

  return (
    <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
      <SonificationControls
        initialMetric={initialMetric}
        onReady={(audioUrl, id) => {
          setUrl(audioUrl);
          setArtifactId(id);
        }}
      />
      <div className="space-y-4">
        <AudioPlayer url={url} label="Playback" />
        <section className="panel p-4 text-sm text-sand/80">
          <p className="section-title">Artifact</p>
          <p className="mt-2">Artifact ID: {artifactId || 'N/A'}</p>
          <p className="mt-1">Audio URL is signed and short-lived by design.</p>
        </section>
      </div>
    </div>
  );
}
