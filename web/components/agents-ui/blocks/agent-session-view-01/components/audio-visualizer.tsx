'use client';

import React from 'react';
import { type MotionProps, motion } from 'motion/react';
import { useVoiceAssistant } from '@livekit/components-react';
import { AgentAudioVisualizerBar } from '@/components/agents-ui/agent-audio-visualizer-bar';
import { cn } from '@/lib/shadcn/utils';

const MotionAgentAudioVisualizerBar = motion.create(AgentAudioVisualizerBar);

interface AudioVisualizerProps extends MotionProps {
  isChatOpen: boolean;
  audioVisualizerBarCount?: number;
  className?: string;
}

// Vaani uses one calm visualizer: a few bars that move with her voice. The colour follows
// the text colour, so it is set in globals.css like everything else.
export function AudioVisualizer({
  audioVisualizerBarCount = 5,
  className,
  ...props
}: AudioVisualizerProps) {
  const { state, audioTrack } = useVoiceAssistant();

  return (
    <MotionAgentAudioVisualizerBar
      size="xl"
      state={state}
      audioTrack={audioTrack}
      barCount={audioVisualizerBarCount}
      className={cn('size-[450px] gap-4 *:min-h-[64px] *:w-[64px]', className)}
      {...props}
    >
      <span className="min-h-2.5 w-2.5 rounded-full bg-current/10 transition-colors duration-250 ease-linear data-[lk-highlighted=true]:bg-current" />
    </MotionAgentAudioVisualizerBar>
  );
}
