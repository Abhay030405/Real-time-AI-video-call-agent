// The one place in the web page that reads settings from web/.env.
// Everything else asks this file. Server side only: none of these names start with
// NEXT_PUBLIC_, so Next.js never sends them to the browser.

export class SettingsError extends Error {}

export interface WebSettings {
  /** "development" is the only value that lets the page start calls (Phase 1 is local only). */
  appEnv: string;
  livekitUrl: string;
  livekitApiKey: string;
  livekitApiSecret: string;
  /** Empty means LiveKit starts the agent automatically for every new room. */
  agentName: string;
  /** How long the access pass for one call stays valid, in seconds. */
  tokenTtlSeconds: number;
}

const REQUIRED = [
  'APP_ENV',
  'LIVEKIT_URL',
  'LIVEKIT_API_KEY',
  'LIVEKIT_API_SECRET',
  'TOKEN_TTL_SECONDS',
] as const;

type Env = Record<string, string | undefined>;

/** Read and check every setting. A missing one stops with a message that names it. */
export function loadSettings(env: Env = process.env): WebSettings {
  if (typeof window !== 'undefined') {
    throw new SettingsError('Settings can only be read on the server side.');
  }
  const missing = REQUIRED.filter((name) => !env[name]);
  if (missing.length > 0) {
    throw new SettingsError(
      `Missing required setting(s) in web/.env: ${missing.join(', ')}. Add them (see web/.env.example).`
    );
  }
  const ttl = Number(env.TOKEN_TTL_SECONDS);
  if (!Number.isInteger(ttl) || ttl <= 0) {
    throw new SettingsError(
      `Setting TOKEN_TTL_SECONDS must be a whole number above 0, got "${env.TOKEN_TTL_SECONDS}".`
    );
  }
  return {
    appEnv: env.APP_ENV as string,
    livekitUrl: env.LIVEKIT_URL as string,
    livekitApiKey: env.LIVEKIT_API_KEY as string,
    livekitApiSecret: env.LIVEKIT_API_SECRET as string,
    agentName: env.AGENT_NAME ?? '',
    tokenTtlSeconds: ttl,
  };
}
