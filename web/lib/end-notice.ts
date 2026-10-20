// What the agent tells the page when it ends a call on its own (see agent/conductor/session.py).
// The page shows a short note and keeps "Start talking" ready.

export const END_TOPIC = 'vaani.session_end';

export interface EndNote {
  reason: string;
  /** When the "come back" offer stops, as Unix seconds. */
  rejoin_until: number;
}

export function parseEndNote(payload: Uint8Array): EndNote | null {
  try {
    const note = JSON.parse(new TextDecoder().decode(payload));
    if (typeof note?.reason === 'string' && typeof note?.rejoin_until === 'number') {
      return note as EndNote;
    }
  } catch {
    // not ours: ignore
  }
  return null;
}

/** Plain words for the person. Returns null once the offer has run out. */
export function endNoticeText(note: EndNote, nowSeconds: number): string | null {
  if (note.reason === 'under_18') return 'This space is for adults, so the call ended. Take care.';
  const minutes = Math.floor((note.rejoin_until - nowSeconds) / 60);
  if (minutes < 1) return null;
  const when = `You can start again in the next ${minutes} minute${minutes === 1 ? '' : 's'}.`;
  if (note.reason === 'stt_failure') {
    return `I could not hear you properly, so I ended the call. ${when}`;
  }
  return `The call ended. ${when}`;
}
