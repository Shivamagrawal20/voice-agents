import { Button } from '@/components/livekit/button';

function WelcomeIllustration() {
  return (
    <div className="relative mb-8 flex w-full max-w-lg flex-col items-center rounded-3xl border border-white/10 bg-gradient-to-br from-white/5 via-white/3 to-white/5 p-8 text-left shadow-[0_25px_80px_rgba(0,0,0,0.35)] backdrop-blur-xl">
      <div className="flex w-full items-center justify-between">
        <div>
          <p className="text-xs uppercase tracking-[0.3em] text-primary/80">
            Falcon Pantry
          </p>
          <h1 className="text-3xl font-bold tracking-tight text-white">
            Night Market Concierge
          </h1>
          <p className="text-sm text-muted-foreground/90">
            Fresh groceries, snacks, and bundles ready for voice checkout.
          </p>
        </div>
        <div className="relative h-24 w-24 rounded-2xl bg-black/30 p-4">
          <svg
            viewBox="0 0 120 120"
            className="h-full w-full text-primary drop-shadow-[0_10px_25px_rgba(255,183,0,0.45)]"
          >
            <path
              d="M20 34h80l-8 60a8 8 0 0 1-8 7H36a8 8 0 0 1-8-7l-8-60Z"
              fill="currentColor"
              opacity="0.85"
            />
            <path
              d="M40 34c0-11 9-20 20-20s20 9 20 20"
              stroke="#FCEFD6"
              strokeWidth="6"
              strokeLinecap="round"
            />
            <circle cx="46" cy="88" r="7" fill="#FCEFD6" />
            <circle cx="82" cy="88" r="7" fill="#FCEFD6" />
            <path
              d="M42 56h36l-4 16H46l-4-16Z"
              fill="#111"
              opacity="0.5"
            />
            <path
              d="M57 26c3-5 11-8 18-5"
              stroke="#84E0C5"
              strokeWidth="5"
              strokeLinecap="round"
            />
          </svg>
        </div>
      </div>
      <div className="mt-6 grid w-full grid-cols-2 gap-4 text-sm">
        <div className="rounded-2xl border border-white/10 bg-white/5 px-4 py-3 text-white/90">
          <p className="text-xs uppercase tracking-wide text-muted-foreground/80">
            Express delivery
          </p>
          <p className="text-lg font-semibold text-white">35 min avg</p>
        </div>
        <div className="rounded-2xl border border-white/10 bg-white/5 px-4 py-3 text-white/90">
          <p className="text-xs uppercase tracking-wide text-muted-foreground/80">
            Cart accuracy
          </p>
          <p className="text-lg font-semibold text-white">Recipe-ready</p>
        </div>
      </div>
    </div>
  );
}

interface WelcomeViewProps {
  startButtonText: string;
  onStartCall: () => void;
}

export const WelcomeView = ({
  startButtonText,
  onStartCall,
  ref,
}: React.ComponentProps<'div'> & WelcomeViewProps) => {
  return (
    <div ref={ref}>
      <section className="bg-transparent flex flex-col items-center justify-center text-center">
        <WelcomeIllustration />

        <p className="text-foreground mb-1 text-sm uppercase tracking-[0.3em] text-primary/70">
          Supermarket voice assistant
        </p>
        <p className="text-foreground max-w-prose pt-2 text-2xl font-semibold leading-tight">
          Build your grocery cart, swap items, or order full recipe kits—
          all hands-free.
        </p>
        <p className="text-muted-foreground max-w-lg pt-3 leading-6 text-sm">
          Ask for pantry staples, bundle ingredients for pasta night, or track earlier orders.
          Sona handles the list while you stay on the move.
        </p>

        <Button
          variant="primary"
          size="lg"
          onClick={onStartCall}
          className="mt-8 w-72 rounded-full font-semibold text-base shadow-[0_15px_45px_rgba(255,183,0,0.35)] transition-all hover:shadow-[0_20px_55px_rgba(255,183,0,0.45)]"
        >
          {startButtonText || 'Start market call'}
        </Button>
      </section>

      <div className="fixed bottom-5 left-0 flex w-full items-center justify-center">
        <p className="text-muted-foreground max-w-prose px-4 pt-1 text-center text-xs font-normal leading-5 text-pretty md:text-sm">
          Crafted for the Murf AI Voice Agent Challenge • Powered by{' '}
          <a
            target="_blank"
            rel="noopener noreferrer"
            href="https://www.murf.ai"
            className="text-primary font-medium hover:underline"
          >
            Murf AI
          </a>
          {' '}Voice Agents & built with{' '}
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
