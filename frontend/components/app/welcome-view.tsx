import { Button } from '@/components/livekit/button';

function WelcomeImage() {
  return (
    <div className="mb-6 flex flex-col items-center">
      {/* Wellness Heart Icon */}
      <svg
        width="80"
        height="80"
        viewBox="0 0 80 80"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        className="text-primary mb-4"
      >
        {/* Heart shape with wellness styling */}
        <path
          d="M40 72C39.5 72 39 71.8 38.6 71.5C20 55 8 42.5 8 28C8 18 16 10 26 10C31.5 10 36.5 12.5 40 16.5C43.5 12.5 48.5 10 54 10C64 10 72 18 72 28C72 42.5 60 55 41.4 71.5C41 71.8 40.5 72 40 72Z"
          fill="currentColor"
          className="drop-shadow-lg"
        />
        {/* Pulse lines for health/wellness effect */}
        <circle cx="40" cy="35" r="3" fill="white" opacity="0.9" />
        <path
          d="M35 30 L40 35 L45 30"
          stroke="white"
          strokeWidth="2"
          strokeLinecap="round"
          fill="none"
          opacity="0.8"
        />
        <path
          d="M30 40 L40 35 L50 40"
          stroke="white"
          strokeWidth="2"
          strokeLinecap="round"
          fill="none"
          opacity="0.8"
        />
      </svg>
      
      {/* HealthifyMe-inspired branding text */}
      <div className="text-center">
        <h1 className="text-3xl font-bold text-foreground mb-2">
          HealthifyMe
        </h1>
        <p className="text-sm text-muted-foreground font-medium">
          Wellness Companion
        </p>
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
      <section className="bg-background flex flex-col items-center justify-center text-center">
        <WelcomeImage />

        <p className="text-foreground max-w-prose pt-4 leading-7 text-lg font-semibold mb-2">
          Your Daily Wellness Check-In Companion
        </p>
        <p className="text-muted-foreground max-w-lg pt-2 leading-6 text-sm">
          Start a conversation with your AI wellness companion. Share your mood, energy, and daily goals for personalized support.
        </p>

        <Button variant="primary" size="lg" onClick={onStartCall} className="mt-8 w-72 font-semibold text-base shadow-lg hover:shadow-xl transition-shadow">
          {startButtonText || "Start Wellness Check-In"}
        </Button>
      </section>

      <div className="fixed bottom-5 left-0 flex w-full items-center justify-center">
        <p className="text-muted-foreground max-w-prose pt-1 text-xs leading-5 font-normal text-pretty md:text-sm text-center px-4">
          Powered by{' '}
          <a
            target="_blank"
            rel="noopener noreferrer"
            href="https://www.murf.ai"
            className="text-primary font-medium hover:underline"
          >
            Murf AI
          </a>
          {' '}Voice Agents • Built with{' '}
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
