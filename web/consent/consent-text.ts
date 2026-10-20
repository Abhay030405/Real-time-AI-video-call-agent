// The words on the consent screen, in plain English. Changing them in a way that matters
// means changing CONSENT_VERSION in lib/consent.ts.

export interface ConsentSection {
  title: string;
  body: string;
}

export const CONSENT_TITLE = 'Before we start';

export const CONSENT_INTRO =
  'This is a private test of Vaani, an AI companion you can talk to for about twenty minutes, in English or Hinglish.';

export const CONSENT_SECTIONS: ConsentSection[] = [
  {
    title: 'Who you are talking to',
    body: 'Vaani is an AI. She is not a person and not a therapist, and she cannot give medical, legal or money advice.',
  },
  {
    title: 'Who can use this',
    body: 'This space is for adults. You must be 18 or older. If you tell Vaani you are under 18, she will end the call kindly.',
  },
  {
    title: 'What happens to your voice',
    body: 'Your voice is turned into text while you talk, so Vaani can reply. The services that do this are Sarvam (speech to text, in India), Cartesia (Vaani’s voice), and an AI model provider, with a backup model through OpenRouter. A small decision model from TypeSafe, a company based in the United States, reads the last few lines of the conversation to help Vaani choose her style. Your camera is not used.',
  },
  {
    title: 'What we keep',
    body: 'For every call we keep timing and cost numbers. In this test we do not save what you said.',
  },
  {
    title: 'If you are in distress',
    body: 'If you talk about hurting yourself, Vaani will share free helplines (Tele-MANAS on 14416, or 112 in an emergency), and the call is marked so the founder can check how it was handled.',
  },
  {
    title: 'You are in control',
    body: 'You can end the call at any time, and you can ask Vaani to forget something you said.',
  },
];

export const CONSENT_CHECKBOX = 'I am 18 or older, and I agree to the above.';
export const CONSENT_BUTTON = 'Continue';
