'use client';

import { RoomAudioRenderer, StartAudio } from '@livekit/components-react';
import type { AppConfig } from '@/app-config';
import { SessionProvider } from '@/components/app/session-provider';
import { ViewController } from '@/components/app/view-controller';
import { Toaster } from '@/components/livekit/toaster';

interface AppProps {
  appConfig: AppConfig;
}

export function App({ appConfig }: AppProps) {
  return (
    <SessionProvider appConfig={appConfig}>
      <main className="relative grid min-h-svh grid-cols-1 place-content-center overflow-hidden bg-gradient-to-br from-[#04060b] via-[#09131a] to-[#0f1f2b] text-foreground">
        <div className="pointer-events-none absolute inset-0 opacity-60">
          <div className="absolute inset-0 bg-[radial-gradient(circle_at_top,_rgba(255,186,0,0.15),_transparent_55%)]" />
          <div className="absolute inset-0 bg-[radial-gradient(circle_at_20%_80%,_rgba(0,155,119,0.25),_transparent_50%)]" />
        </div>
        <div className="pointer-events-none absolute inset-0 opacity-35">
          <div className="h-full w-full bg-[url(/patterns/market-grid.svg)] bg-repeat" />
        </div>
        <div className="relative z-10 px-4 sm:px-6">
          <ViewController />
        </div>
      </main>
      <StartAudio label="Start Audio" />
      <RoomAudioRenderer />
      <Toaster />
    </SessionProvider>
  );
}
