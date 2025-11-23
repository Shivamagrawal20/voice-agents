import { useMemo, useEffect, useState } from 'react';
import { Room, RoomEvent, DataPacket_Kind } from 'livekit-client';
import {
  type ReceivedChatMessage,
  type TextStreamData,
  useChat,
  useRoomContext,
  useTranscriptions,
} from '@livekit/components-react';
import type { ChatOption } from '@/components/livekit/chat-options';

const STORAGE_KEY = 'voice-agent-chat-history';

interface ExtendedChatMessage extends ReceivedChatMessage {
  options?: ChatOption[];
}

function transcriptionToChatMessage(textStream: TextStreamData, room: Room): ExtendedChatMessage {
  // Try to parse options from message metadata or text
  let options: ChatOption[] | undefined;
  try {
    // Check if message contains JSON with options
    const text = textStream.text;
    if (text.includes('__OPTIONS__')) {
      const parts = text.split('__OPTIONS__');
      const optionsJson = parts[1];
      if (optionsJson) {
        options = JSON.parse(optionsJson.trim());
      }
    }
  } catch (e) {
    // Ignore parsing errors
  }

  return {
    id: textStream.streamInfo.id,
    timestamp: textStream.streamInfo.timestamp,
    message: textStream.text.split('__OPTIONS__')[0], // Remove options from message text
    from:
      textStream.participantInfo.identity === room.localParticipant.identity
        ? room.localParticipant
        : Array.from(room.remoteParticipants.values()).find(
            (p) => p.identity === textStream.participantInfo.identity
          ),
    options,
  };
}

export function useChatMessages() {
  const chat = useChat();
  const room = useRoomContext();
  const transcriptions: TextStreamData[] = useTranscriptions();
  const [persistedMessages, setPersistedMessages] = useState<ExtendedChatMessage[]>([]);
  const [optionsMap, setOptionsMap] = useState<Map<string, ChatOption[]>>(new Map());

  // Load persisted messages on mount
  useEffect(() => {
    try {
      const stored = localStorage.getItem(STORAGE_KEY);
      if (stored) {
        const parsed = JSON.parse(stored);
        setPersistedMessages(parsed);
      }
    } catch (e) {
      console.error('Failed to load chat history:', e);
    }
  }, []);

  // Listen for data channel messages containing options
  useEffect(() => {
    if (!room) return;

    const handleDataReceived = (
      payload: Uint8Array,
      participant: any,
      kind: DataPacket_Kind,
      topic?: string
    ) => {
      try {
        const text = new TextDecoder().decode(payload);
        const data = JSON.parse(text);
        
        if (data.type === 'chat_options' && data.options) {
          // Associate options with the most recent agent message
          // We'll use a timestamp-based key
          const key = data.message_id || `options_${Date.now()}`;
          setOptionsMap((prev) => {
            const newMap = new Map(prev);
            newMap.set(key, data.options);
            return newMap;
          });
        }
      } catch (e) {
        // Ignore parsing errors
      }
    };

    room.on(RoomEvent.DataReceived, handleDataReceived);

    return () => {
      room.off(RoomEvent.DataReceived, handleDataReceived);
    };
  }, [room]);

  const mergedTranscriptions = useMemo(() => {
    const merged: Array<ExtendedChatMessage> = [
      ...persistedMessages,
      ...transcriptions.map((transcription) => {
        const msg = transcriptionToChatMessage(transcription, room);
        // Try to find options for this message
        // Match by timestamp (within 2 seconds) and remote participant
        if (!msg.from?.isLocal && !msg.options) {
          const matchingKey = Array.from(optionsMap.keys()).find((key) => {
            const keyTime = parseInt(key.split('_').pop() || '0');
            const timeDiff = Math.abs(msg.timestamp - keyTime);
            return timeDiff < 2000; // Within 2 seconds
          });
          if (matchingKey) {
            msg.options = optionsMap.get(matchingKey);
          }
        }
        return msg;
      }),
      ...chat.chatMessages.map((msg) => ({
        ...msg,
        options: undefined,
      })),
    ];
    return merged.sort((a, b) => a.timestamp - b.timestamp);
  }, [transcriptions, chat.chatMessages, room, persistedMessages, optionsMap]);

  // Persist messages to localStorage
  useEffect(() => {
    try {
      // Only persist messages that are not from current session (to avoid duplicates)
      const toPersist = mergedTranscriptions.filter((msg) => {
        const isRecent = Date.now() - msg.timestamp < 5000; // Don't persist very recent messages
        return !isRecent;
      });
      if (toPersist.length > 0) {
        localStorage.setItem(STORAGE_KEY, JSON.stringify(toPersist));
      }
    } catch (e) {
      console.error('Failed to persist chat history:', e);
    }
  }, [mergedTranscriptions]);

  return mergedTranscriptions;
}
