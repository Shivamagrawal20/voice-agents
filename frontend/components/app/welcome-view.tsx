import React from 'react';
import { Button } from '@/components/livekit/button';

function WelcomeIllustration() {
  return (
    <div className="relative mb-8 flex w-full max-w-lg flex-col items-center rounded-3xl border border-white/10 bg-gradient-to-br from-white/5 via-white/3 to-white/5 p-8 text-left shadow-[0_25px_80px_rgba(0,0,0,0.35)] backdrop-blur-xl">
      <div className="flex w-full items-center justify-between">
        <div>
          <p className="text-primary/80 text-xs tracking-[0.3em] uppercase">
            AI Voice Agent Challenge
          </p>
          <h1 className="text-3xl font-bold tracking-tight text-white">Day 10: Improv Battle</h1>
          <p className="text-muted-foreground/90 text-sm">
            Step onto the improv stage with a high-energy AI host powered by the fastest TTS API -
            Murf Falcon.
          </p>
        </div>
        <div className="relative h-24 w-24 rounded-2xl bg-black/30 p-4">
          <svg
            viewBox="0 0 120 120"
            className="text-primary h-full w-full drop-shadow-[0_10px_25px_rgba(255,183,0,0.45)]"
          >
            {/* D20 Dice Icon */}
            <path
              d="M60 10 L90 30 L90 60 L60 80 L30 60 L30 30 Z"
              fill="currentColor"
              opacity="0.9"
            />
            <path
              d="M60 10 L60 80 M30 30 L90 30 M30 60 L90 60"
              stroke="#FCEFD6"
              strokeWidth="3"
              strokeLinecap="round"
            />
            <circle cx="60" cy="45" r="8" fill="#FCEFD6" />
            <circle cx="45" cy="55" r="6" fill="#FCEFD6" />
            <circle cx="75" cy="55" r="6" fill="#FCEFD6" />
          </svg>
        </div>
      </div>
      <div className="mt-6 grid w-full grid-cols-2 gap-4 text-sm">
        <div className="rounded-2xl border border-white/10 bg-white/5 px-4 py-3 text-white/90">
          <p className="text-muted-foreground/80 text-xs tracking-wide uppercase">
            Interactive Story
          </p>
          <p className="text-lg font-semibold text-white">8-15 Turns</p>
        </div>
        <div className="rounded-2xl border border-white/10 bg-white/5 px-4 py-3 text-white/90">
          <p className="text-muted-foreground/80 text-xs tracking-wide uppercase">World State</p>
          <p className="text-lg font-semibold text-white">Persistent</p>
        </div>
      </div>
    </div>
  );
}

interface WelcomeViewProps {
  startButtonText: string;
  onStartCall: () => void;
  playerName: string;
  onPlayerNameChange: (name: string) => void;
}

export const WelcomeView = ({
  startButtonText,
  onStartCall,
  playerName,
  onPlayerNameChange,
  ref,
}: React.ComponentProps<'div'> & WelcomeViewProps) => {
  return (
    <div ref={ref}>
      <section className="flex flex-col items-center justify-center bg-transparent text-center">
        <WelcomeIllustration />

        <p className="text-primary/70 mb-1 text-sm tracking-[0.3em] uppercase">
          Powered by Murf Falcon
        </p>
        <p className="text-foreground max-w-prose pt-2 text-2xl leading-tight font-semibold">
          Play a short-form improv game show with your AI host. Act out wild scenarios and hear how
          the host reacts to your performance.
        </p>
        <p className="text-muted-foreground max-w-lg pt-3 text-sm leading-6">
          Join as a contestant, improvise scenes like a time-travelling tour guide or a cursed
          customer, and get a mix of praise, playful teasing, and honest feedback. Say “end scene”
          when you want to move to the next round or “stop game” to wrap up early.
        </p>

        <div className="mt-6 flex w-full max-w-sm flex-col gap-2 text-left">
          <label className="text-muted-foreground text-xs font-medium tracking-wide uppercase">
            Name
          </label>
          <input
            type="text"
            value={playerName}
            onChange={(e) => onPlayerNameChange(e.target.value)}
            placeholder="Enter your stage name"
            className="bg-background/80 text-foreground focus:border-primary w-full rounded-xl border border-white/20 px-4 py-2 text-sm shadow-[0_8px_25px_rgba(0,0,0,0.35)] ring-0 outline-none placeholder:text-white/40 focus:outline-none"
          />
        </div>

        <Button
          variant="primary"
          size="lg"
          onClick={onStartCall}
          className="mt-8 w-72 rounded-full text-base font-semibold shadow-[0_15px_45px_rgba(255,183,0,0.35)] transition-all hover:shadow-[0_20px_55px_rgba(255,183,0,0.45)]"
        >
          {startButtonText || 'Start Improv Battle'}
        </Button>
      </section>

      <div className="fixed bottom-5 left-0 flex w-full items-center justify-center">
        <p className="text-muted-foreground max-w-prose px-4 pt-1 text-center text-xs leading-5 font-normal text-pretty md:text-sm">
          Crafted for the Murf AI Voice Agent Challenge • Powered by{' '}
          <a
            target="_blank"
            rel="noopener noreferrer"
            href="https://www.murf.ai"
            className="text-primary font-medium hover:underline"
          >
            Murf AI
          </a>{' '}
          Voice Agents & built with{' '}
          <a
            target="_blank"
            rel="noopener noreferrer"
            href="https://livekit.io"
            className="text-primary font-medium hover:underline"
          >
            LiveKit
          </a>
        </p>
      </div>
    </div>
  );
};
