// The consent the person gives before a call. The version is bumped whenever the wording
// changes in a way that matters (for example when spoken words start being saved), so every
// call records which wording the person agreed to.

export const CONSENT_VERSION = 'consent_v1';

export interface ConsentAgreement {
  version: string;
  adult: boolean;
}

/** True only for the current wording, with the adult box ticked. Used by the token route. */
export function isValidConsent(value: unknown): value is ConsentAgreement {
  if (typeof value !== 'object' || value === null) return false;
  const { version, adult } = value as Partial<ConsentAgreement>;
  return version === CONSENT_VERSION && adult === true;
}
