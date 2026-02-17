import { API_BASE, WORKSPACE_ID } from '@/lib/api';
import { EventMessage } from '@/lib/types';

export function subscribeEvents(onEvent: (event: EventMessage) => void): () => void {
  const url = `${API_BASE}/events/sse?workspace_id=${encodeURIComponent(WORKSPACE_ID)}`;
  const source = new EventSource(url);

  source.onmessage = (message) => {
    try {
      const parsed = JSON.parse(message.data) as EventMessage;
      onEvent(parsed);
    } catch {
      // keep stream alive on parse issues
    }
  };

  source.addEventListener('anomaly.detected', (message) => {
    try {
      const parsed = JSON.parse((message as MessageEvent).data) as EventMessage;
      onEvent(parsed);
    } catch {
      // noop
    }
  });

  source.onerror = () => {
    // browser reconnect policy handles retries
  };

  return () => source.close();
}
