import { TokenVerifier } from 'livekit-server-sdk';
import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import { POST } from '@/app/api/token/route';

const KEY = 'devkey';
const SECRET = 'a-long-test-secret-value-for-signing';

function setEnv(overrides: Record<string, string | undefined> = {}) {
  const env: Record<string, string | undefined> = {
    APP_ENV: 'development',
    LIVEKIT_URL: 'ws://localhost:7880',
    LIVEKIT_API_KEY: KEY,
    LIVEKIT_API_SECRET: SECRET,
    TOKEN_TTL_SECONDS: '600',
    ...overrides,
  };
  for (const [name, value] of Object.entries(env)) {
    if (value === undefined) delete process.env[name];
    else process.env[name] = value;
  }
}

const request = () =>
  new Request('http://localhost/api/token', { method: 'POST', body: JSON.stringify({}) });

describe('POST /api/token', () => {
  const saved = { ...process.env };
  beforeEach(() => setEnv());
  afterEach(() => {
    process.env = { ...saved };
  });

  it('returns a pass for one room, microphone only, lasting the set time', async () => {
    const response = await POST(request());
    expect(response.status).toBe(200);
    expect(response.headers.get('Cache-Control')).toBe('no-store');
    const body = await response.json();
    expect(body.serverUrl).toBe('ws://localhost:7880');
    expect(body.roomName).toMatch(/^vaani_[0-9a-f-]{36}$/);

    const claims = await new TokenVerifier(KEY, SECRET).verify(body.participantToken);
    expect(claims.video?.room).toBe(body.roomName);
    expect(claims.video?.roomJoin).toBe(true);
    expect(claims.video?.canPublishSources).toEqual(['microphone']);
    expect((claims.exp ?? 0) - (claims.nbf ?? 0)).toBe(600);
  });

  it('gives every call its own room', async () => {
    const a = await (await POST(request())).json();
    const b = await (await POST(request())).json();
    expect(a.roomName).not.toBe(b.roomName);
  });

  it('refuses outside development', async () => {
    setEnv({ APP_ENV: 'production' });
    expect((await POST(request())).status).toBe(403);
  });

  it('names a missing setting', async () => {
    setEnv({ LIVEKIT_API_SECRET: undefined });
    const response = await POST(request());
    expect(response.status).toBe(500);
    expect(await response.text()).toContain('LIVEKIT_API_SECRET');
  });
});
