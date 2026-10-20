'use client';

import { useState } from 'react';
import { Button } from '@/components/ui/button';
import {
  CONSENT_BUTTON,
  CONSENT_CHECKBOX,
  CONSENT_INTRO,
  CONSENT_SECTIONS,
  CONSENT_TITLE,
} from './consent-text';

interface ConsentViewProps {
  onAgree: () => void;
}

export function ConsentView({ onAgree }: ConsentViewProps) {
  const [ticked, setTicked] = useState(false);

  return (
    <section className="bg-background mx-auto flex max-w-xl flex-col gap-6 px-6 py-10">
      <h1 className="text-foreground font-display text-3xl leading-tight font-normal md:text-4xl">
        {CONSENT_TITLE}
      </h1>
      <p className="text-muted-foreground leading-7">{CONSENT_INTRO}</p>

      <div className="flex flex-col gap-4">
        {CONSENT_SECTIONS.map((section) => (
          <div key={section.title}>
            <h2 className="text-foreground font-semibold">{section.title}</h2>
            <p className="text-muted-foreground leading-7">{section.body}</p>
          </div>
        ))}
      </div>

      <label className="text-foreground flex cursor-pointer items-start gap-3 leading-6">
        <input
          type="checkbox"
          checked={ticked}
          onChange={(event) => setTicked(event.target.checked)}
          className="accent-primary mt-1 size-5"
        />
        <span>{CONSENT_CHECKBOX}</span>
      </label>

      <Button
        size="lg"
        disabled={!ticked}
        onClick={onAgree}
        className="w-64 rounded-full font-mono text-xs font-bold tracking-wider uppercase"
      >
        {CONSENT_BUTTON}
      </Button>
    </section>
  );
}
