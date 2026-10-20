// Remembers in this browser tab that the person agreed to the current wording, so a refresh
// does not ask again. The server still checks the agreement on every call.
import { CONSENT_VERSION } from '@/lib/consent';

const KEY = 'vaani.consent';

export function hasAgreed(): boolean {
  try {
    return window.sessionStorage.getItem(KEY) === CONSENT_VERSION;
  } catch {
    return false; // storage can be blocked: just ask again
  }
}

export function rememberAgreement(): void {
  try {
    window.sessionStorage.setItem(KEY, CONSENT_VERSION);
  } catch {
    // not remembered; the person will be asked again next time
  }
}
