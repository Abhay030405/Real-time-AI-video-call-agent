'use client';

import { useMemo, useState } from 'react';
import { TokenSource } from 'livekit-client';
import { useDataChannel, useSession } from '@livekit/components-react';
import { WarningIcon } from '@phosphor-icons/react/dist/ssr';
import { AgentSessionProvider } from '@/components/agents-ui/agent-session-provider';
import { StartAudioButton } from '@/components/agents-ui/start-audio-button';
import { ViewController } from '@/components/app/view-controller';
import { Toaster } from '@/components/ui/sonner';
import { useAgentErrors } from '@/hooks/useAgentErrors';
import { useDebugMode } from '@/hooks/useDebug';
import { END_TOPIC, type EndNote, endNoticeText, parseEndNote } from '@/lib/end-notice';

const IN_DEVELOPMENT = process.env.NODE_ENV !== 'production';

function AppSetup() {
  useDebugMode({ enabled: IN_DEVELOPMENT });
  useAgentErrors();

  return null;
}

// Hears the note the agent sends when it ends a call on its own
function EndWatcher({ onEnd }: { onEnd: (note: EndNote) => void }) {
  useDataChannel(END_TOPIC, (message) => {
    const note = parseEndNote(message.payload);
    if (note) onEnd(note);
  });

  return null;
}

interface AppProps {
  tokenEndpoint: string;
  agentName?: string;
}

export function App({ tokenEndpoint, agentName }: AppProps) {
  const tokenSource = useMemo(() => TokenSource.endpoint(tokenEndpoint), [tokenEndpoint]);

  const session = useSession(tokenSource, agentName ? { agentName } : undefined);
  const [endNote, setEndNote] = useState<EndNote | null>(null);
  const notice = endNote ? endNoticeText(endNote, Math.floor(Date.now() / 1000)) : null;

  return (
    <AgentSessionProvider session={session}>
      <AppSetup />
      <EndWatcher onEnd={setEndNote} />
      <main className="grid h-svh grid-cols-1 place-content-center">
        <ViewController notice={notice} onStart={() => setEndNote(null)} />
      </main>
      <StartAudioButton label="Start Audio" />
      <Toaster
        icons={{
          warning: <WarningIcon weight="bold" />,
        }}
        position="top-center"
        className="toaster group"
      />
    </AgentSessionProvider>
  );
}
