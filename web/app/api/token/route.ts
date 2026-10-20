import { NextResponse } from 'next/server';
import { AccessToken, RoomConfiguration, TrackSource } from 'livekit-server-sdk';
import { randomUUID } from 'node:crypto';
import { CONSENT_VERSION, isValidConsent } from '@/lib/consent';
import { SettingsError, loadSettings } from '@/lib/settings';

// Makes the short-lived access pass for one call. It runs only on our server, so the
// LiveKit key and secret never reach the browser.
//
// Phase 1 is local only: the route refuses unless APP_ENV is "development". A proper
// login for testers is added before Phase 5.

export const revalidate = 0; // never cache a pass

const NO_STORE = { 'Cache-Control': 'no-store' };

export async function POST(req: Request) {
  let settings;
  try {
    settings = loadSettings();
  } catch (error) {
    const message = error instanceof SettingsError ? error.message : 'Settings could not be read.';
    return new NextResponse(message, { status: 500, headers: NO_STORE });
  }

  if (settings.appEnv !== 'development') {
    return new NextResponse('Calls are not open yet.', { status: 403, headers: NO_STORE });
  }

  const body = await req.json().catch(() => ({}));
  // No call without the person's agreement to the current consent wording (adults only)
  if (!isValidConsent(body?.consent)) {
    return new NextResponse('Please read and agree to the consent screen first.', {
      status: 403,
      headers: NO_STORE,
    });
  }
  const roomConfig = body?.room_config
    ? RoomConfiguration.fromJson(body.room_config, { ignoreUnknownFields: true })
    : new RoomConfiguration();

  // Random, unguessable names: one new room per call
  const participantName = 'user';
  const participantIdentity = `vaani_user_${randomUUID()}`;
  const roomName = `vaani_${randomUUID()}`;

  const token = new AccessToken(settings.livekitApiKey, settings.livekitApiSecret, {
    identity: participantIdentity,
    name: participantName,
    ttl: `${settings.tokenTtlSeconds}s`,
    // The agent records which wording this person agreed to, and refuses a call without it
    attributes: { consent_version: CONSENT_VERSION },
  });
  token.addGrant({
    room: roomName,
    roomJoin: true,
    canSubscribe: true,
    canPublish: true,
    canPublishData: true, // text messages and, later, the Reading Engine data channel
    canPublishSources: [TrackSource.MICROPHONE], // no camera or screen share in version 0
  });
  token.roomConfig = roomConfig;

  return NextResponse.json(
    {
      serverUrl: settings.livekitUrl,
      roomName,
      participantName,
      participantToken: await token.toJwt(),
    },
    { headers: NO_STORE }
  );
}
