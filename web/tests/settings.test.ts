import { describe, expect, it } from 'vitest';
import { SettingsError, loadSettings } from '@/lib/settings';

const GOOD = {
  APP_ENV: 'development',
  LIVEKIT_URL: 'ws://localhost:7880',
  LIVEKIT_API_KEY: 'devkey',
  LIVEKIT_API_SECRET: 'a-long-test-secret-value-for-signing',
  TOKEN_TTL_SECONDS: '600',
};

describe('loadSettings', () => {
  it('reads every setting', () => {
    const s = loadSettings(GOOD);
    expect(s.livekitUrl).toBe('ws://localhost:7880');
    expect(s.tokenTtlSeconds).toBe(600);
    expect(s.agentName).toBe('');
  });

  it('names every missing setting', () => {
    expect(() => loadSettings({ ...GOOD, LIVEKIT_URL: '', LIVEKIT_API_KEY: undefined })).toThrow(
      /LIVEKIT_URL, LIVEKIT_API_KEY/
    );
  });

  it('rejects a pass length that is not a whole number above zero', () => {
    for (const bad of ['abc', '0', '-5', '1.5']) {
      expect(() => loadSettings({ ...GOOD, TOKEN_TTL_SECONDS: bad })).toThrow(SettingsError);
    }
  });
});
