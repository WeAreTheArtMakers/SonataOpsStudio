'use client';

import { useState } from 'react';

import CopilotChat from '@/components/CopilotChat';
import SourcesPanel from '@/components/SourcesPanel';
import { SourceItem } from '@/lib/types';

export default function CopilotPage() {
  const [sources, setSources] = useState<SourceItem[]>([]);

  return (
    <div className="grid grid-cols-1 gap-4 xl:grid-cols-[1.4fr_1fr]">
      <CopilotChat onSources={setSources} />
      <SourcesPanel sources={sources} />
    </div>
  );
}
