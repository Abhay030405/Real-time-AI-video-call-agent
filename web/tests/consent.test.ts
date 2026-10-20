import { describe, expect, it } from 'vitest';
import { CONSENT_SECTIONS, CONSENT_TITLE } from '@/consent/consent-text';
import { CONSENT_VERSION, isValidConsent } from '@/lib/consent';

describe('consent', () => {
  it('accepts only the current wording with the adult box ticked', () => {
    expect(isValidConsent({ version: CONSENT_VERSION, adult: true })).toBe(true);
    expect(isValidConsent({ version: CONSENT_VERSION, adult: false })).toBe(false);
    expect(isValidConsent({ version: 'old', adult: true })).toBe(false);
    expect(isValidConsent(null)).toBe(false);
    expect(isValidConsent(undefined)).toBe(false);
  });

  it('tells the person what the design says it must (adults only, vendors, flags)', () => {
    const text = [CONSENT_TITLE, ...CONSENT_SECTIONS.map((s) => `${s.title} ${s.body}`)].join(' ');
    for (const needed of [
      '18',
      'AI',
      'not a therapist',
      'Sarvam',
      'Cartesia',
      'TypeSafe',
      'United States',
      '14416',
      'founder',
      'camera',
    ]) {
      expect(text).toContain(needed);
    }
  });
});
