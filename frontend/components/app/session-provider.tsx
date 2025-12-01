'use client';

import { createContext, useContext, useMemo, useState } from 'react';
import { RoomContext } from '@livekit/components-react';
import { APP_CONFIG_DEFAULTS, type AppConfig } from '@/app-config';
import { useRoom } from '@/hooks/useRoom';

const SessionContext = createContext<{
  appConfig: AppConfig;
  isSessionActive: boolean;
  startSession: () => void;
  endSession: () => void;
  playerName: string;
  setPlayerName: (name: string) => void;
}>({
  appConfig: APP_CONFIG_DEFAULTS,
  isSessionActive: false,
  startSession: () => {},
  endSession: () => {},
  playerName: '',
  setPlayerName: () => {},
});

interface SessionProviderProps {
  appConfig: AppConfig;
  children: React.ReactNode;
}

export const SessionProvider = ({ appConfig, children }: SessionProviderProps) => {
  const [playerName, setPlayerName] = useState('');
  const { room, isSessionActive, startSession, endSession } = useRoom(appConfig, playerName);
  const contextValue = useMemo(
    () => ({ appConfig, isSessionActive, startSession, endSession, playerName, setPlayerName }),
    [appConfig, isSessionActive, startSession, endSession, playerName]
  );

  return (
    <RoomContext.Provider value={room}>
      <SessionContext.Provider value={contextValue}>{children}</SessionContext.Provider>
    </RoomContext.Provider>
  );
};

export function useSession() {
  return useContext(SessionContext);
}
