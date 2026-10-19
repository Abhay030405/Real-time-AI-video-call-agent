import { describe, expect, it } from 'vitest';
import { endNoticeText, parseEndNote } from '@/lib/end-notice';

const encode = (value: unknown) => new TextEncoder().encode(JSON.stringify(value));

describe('end notice', () => {
  it('reads a note from the agent', () => {
    expect(parseEndNote(encode({ reason: 'stt_failure', rejoin_until: 100 }))).toEqual({
      reason: 'stt_failure',
      rejoin_until: 100,
    });
  });

  it('ignores anything that is not a note', () => {
    expect(parseEndNote(new TextEncoder().encode('hello'))).toBeNull();
    expect(parseEndNote(encode({ reason: 5 }))).toBeNull();
  });

  it('says why the call ended and how long the offer lasts', () => {
    const text = endNoticeText({ reason: 'stt_failure', rejoin_until: 1800 }, 0);
    expect(text).toContain('could not hear you');
    expect(text).toContain('30 minutes');
  });

  it('stops offering when the time is up', () => {
    expect(endNoticeText({ reason: 'stt_failure', rejoin_until: 1000 }, 990)).toBeNull();
    expect(endNoticeText({ reason: 'stt_failure', rejoin_until: 1000 }, 2000)).toBeNull();
  });
});
