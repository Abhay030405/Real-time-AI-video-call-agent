import { App } from '@/components/app/app';
import { loadSettings } from '@/lib/settings';

// The page fetches its access pass from our own token route. The agent name comes from
// web/.env (empty means LiveKit starts the agent automatically).
export const dynamic = 'force-dynamic';

export default function Page() {
  const { agentName } = loadSettings();
  return <App tokenEndpoint="/api/token" agentName={agentName || undefined} />;
}
