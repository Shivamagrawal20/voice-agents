'use client';

import { type HTMLAttributes, useCallback, useEffect, useState } from 'react';
import { Track } from 'livekit-client';
import { useChat, useRemoteParticipants } from '@livekit/components-react';
import { ChatTextIcon, PhoneDisconnectIcon } from '@phosphor-icons/react/dist/ssr';
import { useSession } from '@/components/app/session-provider';
import { TrackToggle } from '@/components/livekit/agent-control-bar/track-toggle';
import { Button } from '@/components/livekit/button';
import { Toggle } from '@/components/livekit/toggle';
import { cn } from '@/lib/utils';
import { ChatInput } from './chat-input';
import { UseInputControlsProps, useInputControls } from './hooks/use-input-controls';
import { usePublishPermissions } from './hooks/use-publish-permissions';
import { TrackSelector } from './track-selector';

export interface ControlBarControls {
  leave?: boolean;
  camera?: boolean;
  microphone?: boolean;
  screenShare?: boolean;
  chat?: boolean;
}

export interface AgentControlBarProps extends UseInputControlsProps {
  controls?: ControlBarControls;
  onDisconnect?: () => void;
  onChatOpenChange?: (open: boolean) => void;
  onDeviceError?: (error: { source: Track.Source; error: Error }) => void;
}

/**
 * A control bar specifically designed for voice assistant interfaces
 */
export function AgentControlBar({
  controls,
  saveUserChoices = true,
  className,
  onDisconnect,
  onDeviceError,
  onChatOpenChange,
  ...props
}: AgentControlBarProps & HTMLAttributes<HTMLDivElement>) {
  const { send } = useChat();
  const participants = useRemoteParticipants();
  const [chatOpen, setChatOpen] = useState(false);
  const [cartPanelOpen, setCartPanelOpen] = useState(false);
  const [showOrderBanner, setShowOrderBanner] = useState(false);
  const [catalog, setCatalog] = useState<
    Array<{
      id: string;
      name: string;
      category?: string;
      price?: number;
      unit?: string;
      tags?: string[];
    }>
  >([]);
  const [isCatalogLoading, setIsCatalogLoading] = useState(false);
  const [catalogError, setCatalogError] = useState<string | null>(null);
  const publishPermissions = usePublishPermissions();
  const { isSessionActive, endSession } = useSession();

  const {
    micTrackRef,
    cameraToggle,
    microphoneToggle,
    screenShareToggle,
    handleAudioDeviceChange,
    handleVideoDeviceChange,
    handleMicrophoneDeviceSelectError,
    handleCameraDeviceSelectError,
  } = useInputControls({ onDeviceError, saveUserChoices });

  const handleSendMessage = async (message: string) => {
    await send(message);
  };

  const handleQuickOrder = async () => {
    // Ask the agent to place the current cart as an order.
    await handleSendMessage('Please place my current grocery order now.');
    setCartPanelOpen(false);
    setShowOrderBanner(true);
  };

  useEffect(() => {
    if (!showOrderBanner) return;
    const timeout = setTimeout(() => setShowOrderBanner(false), 6000);
    return () => clearTimeout(timeout);
  }, [showOrderBanner]);

  useEffect(() => {
    if (!cartPanelOpen || catalog.length > 0 || isCatalogLoading) return;
    const load = async () => {
      try {
        setIsCatalogLoading(true);
        setCatalogError(null);
        const res = await fetch('/api/catalog');
        if (!res.ok) {
          throw new Error(`HTTP ${res.status}`);
        }
        const data = (await res.json()) as { items?: any[] };
        setCatalog((data.items || []) as any[]);
      } catch (e) {
        console.error('Failed to fetch catalog', e);
        setCatalogError('Unable to load store items right now.');
      } finally {
        setIsCatalogLoading(false);
      }
    };
    void load();
  }, [cartPanelOpen, catalog.length, isCatalogLoading]);

  const handleToggleTranscript = useCallback(
    (open: boolean) => {
      setChatOpen(open);
      onChatOpenChange?.(open);
    },
    [onChatOpenChange, setChatOpen]
  );

  const handleDisconnect = useCallback(async () => {
    endSession();
    onDisconnect?.();
  }, [endSession, onDisconnect]);

  const visibleControls = {
    leave: controls?.leave ?? true,
    microphone: controls?.microphone ?? publishPermissions.microphone,
    screenShare: controls?.screenShare ?? publishPermissions.screenShare,
    camera: controls?.camera ?? publishPermissions.camera,
    chat: controls?.chat ?? publishPermissions.data,
  };

  const isAgentAvailable = participants.some((p) => p.isAgent);

  return (
    <div className="relative">
      {showOrderBanner && (
        <div className="pointer-events-none absolute -top-12 left-1/2 z-40 w-[min(100%,24rem)] -translate-x-1/2 rounded-2xl border border-emerald-400/30 bg-emerald-500/15 px-4 py-3 text-xs text-emerald-50 shadow-[0_18px_40px_rgba(0,0,0,0.55)] backdrop-blur-xl">
          <p className="font-semibold">Thanks for shopping with Falcon Pantry.</p>
          <p className="mt-1 text-[0.7rem] text-emerald-100/80">
            Your grocery order is being prepared and should arrive in about 15 minutes.
          </p>
        </div>
      )}

      {/* Cart quick actions panel */}
      {cartPanelOpen && (
        <div className="fixed inset-0 z-40 flex items-end justify-center bg-black/50 px-4 pb-24 sm:items-center sm:bg-black/60">
          <div className="w-full max-w-md rounded-3xl border border-white/10 bg-card/95 p-5 text-left text-sm text-white shadow-[0_24px_60px_rgba(0,0,0,0.75)] backdrop-blur-2xl">
            <div className="mb-3 flex items-center justify-between gap-3">
              <div>
                <p className="text-[0.65rem] uppercase tracking-[0.35em] text-primary/80">
                  Cart preview
                </p>
                <h3 className="text-lg font-semibold text-white">Selected items</h3>
              </div>
              <button
                type="button"
                onClick={() => setCartPanelOpen(false)}
                className="rounded-full border border-white/15 bg-white/5 px-2 py-1 text-[0.65rem] font-medium text-white/80 hover:bg-white/10"
              >
                Close
              </button>
            </div>
            <p className="text-xs text-white/80">
              Tap an item below to ask Sona to drop it into your live cart. She&apos;ll keep
              quantities and totals in sync.
            </p>

            <div className="mt-4 max-h-60 space-y-1 overflow-y-auto rounded-2xl border border-white/10 bg-black/30 p-2">
              {isCatalogLoading && (
                <p className="px-2 py-1 text-xs text-white/70">Loading store items…</p>
              )}
              {catalogError && (
                <p className="px-2 py-1 text-xs text-red-300">{catalogError}</p>
              )}
              {!isCatalogLoading &&
                !catalogError &&
                catalog.map((item) => (
                  <div
                    key={item.id}
                    className="flex items-center justify-between gap-2 rounded-xl px-3 py-2 text-xs text-white/90 hover:bg-white/5"
                  >
                    <div>
                      <p className="font-medium">{item.name}</p>
                      <p className="text-[0.7rem] text-white/60">
                        {item.category}{' '}
                        {typeof item.price === 'number'
                          ? `• $${item.price.toFixed(2)}${item.unit ? ` / ${item.unit}` : ''}`
                          : ''}
                      </p>
                    </div>
                    <button
                      type="button"
                      onClick={() =>
                        handleSendMessage(
                          `Please add 1 unit of catalog item "${item.name}" (id: ${item.id}) to my cart.`
                        )
                      }
                      className="rounded-full bg-primary px-3 py-1 text-[0.7rem] font-semibold text-primary-foreground shadow-[0_8px_25px_rgba(255,183,0,0.45)] hover:brightness-110"
                    >
                      Add
                    </button>
                  </div>
                ))}
            </div>

            <div className="mt-4 flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
              <button
                type="button"
                onClick={() => handleSendMessage('What is currently in my cart?')}
                className="inline-flex items-center justify-center rounded-full border border-white/15 bg-white/5 px-4 py-2 text-[0.75rem] font-medium text-white hover:bg-white/10"
              >
                Ask Sona to read cart
              </button>
              <button
                type="button"
                onClick={handleQuickOrder}
                className="inline-flex items-center justify-center rounded-full bg-primary px-5 py-2 text-[0.78rem] font-semibold text-primary-foreground shadow-[0_12px_35px_rgba(255,183,0,0.5)] hover:brightness-110"
              >
                Place order now
              </button>
            </div>
          </div>
        </div>
      )}

      <div
        aria-label="Voice assistant controls"
        className={cn(
          'bg-background border-input/50 dark:border-muted flex flex-col rounded-[31px] border p-3 drop-shadow-md/3',
          className
        )}
        {...props}
      >
      {/* Chat Input */}
      {visibleControls.chat && (
        <ChatInput
          chatOpen={chatOpen}
          isAgentAvailable={isAgentAvailable}
          onSend={handleSendMessage}
        />
      )}

      <div className="flex gap-1">
        <div className="flex grow gap-1">
          {/* Toggle Microphone */}
          {visibleControls.microphone && (
            <TrackSelector
              kind="audioinput"
              aria-label="Toggle microphone"
              source={Track.Source.Microphone}
              pressed={microphoneToggle.enabled}
              disabled={microphoneToggle.pending}
              audioTrackRef={micTrackRef}
              onPressedChange={microphoneToggle.toggle}
              onMediaDeviceError={handleMicrophoneDeviceSelectError}
              onActiveDeviceChange={handleAudioDeviceChange}
            />
          )}

          {/* Toggle Camera */}
          {visibleControls.camera && (
            <TrackSelector
              kind="videoinput"
              aria-label="Toggle camera"
              source={Track.Source.Camera}
              pressed={cameraToggle.enabled}
              pending={cameraToggle.pending}
              disabled={cameraToggle.pending}
              onPressedChange={cameraToggle.toggle}
              onMediaDeviceError={handleCameraDeviceSelectError}
              onActiveDeviceChange={handleVideoDeviceChange}
            />
          )}

          {/* Toggle Screen Share */}
          {visibleControls.screenShare && (
            <TrackToggle
              size="icon"
              variant="secondary"
              aria-label="Toggle screen share"
              source={Track.Source.ScreenShare}
              pressed={screenShareToggle.enabled}
              disabled={screenShareToggle.pending}
              onPressedChange={screenShareToggle.toggle}
            />
          )}

          {/* Toggle Transcript */}
          <Toggle
            size="icon"
            variant="secondary"
            aria-label="Toggle transcript"
            pressed={chatOpen}
            onPressedChange={handleToggleTranscript}
          >
            <ChatTextIcon weight="bold" />
          </Toggle>

          {/* Cart quick actions */}
          <Button
            size="icon"
            type="button"
            variant="secondary"
            aria-label="View cart and place order"
            className="ml-1"
            onClick={() => setCartPanelOpen(true)}
            disabled={!isSessionActive || !isAgentAvailable}
          >
            <span className="font-mono text-xs">🛒</span>
          </Button>
        </div>

        {/* Disconnect */}
        {visibleControls.leave && (
          <Button
            variant="destructive"
            onClick={handleDisconnect}
            disabled={!isSessionActive}
            className="font-mono"
          >
            <PhoneDisconnectIcon weight="bold" />
            <span className="hidden md:inline">END CALL</span>
            <span className="inline md:hidden">END</span>
          </Button>
        )}
      </div>
      </div>
    </div>
  );
}
