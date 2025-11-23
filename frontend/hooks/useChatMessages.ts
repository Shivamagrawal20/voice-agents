import { useMemo, useEffect, useState, useRef } from 'react';
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
  const [optionsMap, setOptionsMap] = useState<Map<string, any>>(new Map());
  const usedOptionsRef = useRef<Set<string>>(new Set());

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
          // Store options with message text for better matching
          const key = data.message_id || `options_${Date.now()}`;
          setOptionsMap((prev) => {
            const newMap = new Map(prev);
            // Store with both timestamp and message text for matching
            newMap.set(key, {
              options: data.options,
              messageText: data.message_text || '',
              timestamp: Date.now()
            });
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

  // Clean up used and expired options from map
  useEffect(() => {
    if (optionsMap.size === 0) return;
    
    const now = Date.now();
    setOptionsMap((prev) => {
      const newMap = new Map(prev);
      let changed = false;
      for (const [key, _] of newMap.entries()) {
        // Remove if used or expired
        if (usedOptionsRef.current.has(key)) {
          newMap.delete(key);
          usedOptionsRef.current.delete(key);
          changed = true;
        } else {
          const keyTime = parseInt(key.split('_').pop() || '0');
          if (now - keyTime > 5000) {
            newMap.delete(key);
            changed = true;
          }
        }
      }
      return changed ? newMap : prev;
    });
  }, [transcriptions, optionsMap]);

  const mergedTranscriptions = useMemo(() => {
    const merged: Array<ExtendedChatMessage> = [
      ...persistedMessages,
      ...transcriptions.map((transcription) => {
        const msg = transcriptionToChatMessage(transcription, room);
        // Try to find options for this message
        // First check if options are embedded in the message text
        if (msg.options) {
          return msg; // Options already parsed from text
        }
        
        // If no embedded options, try to match from data channel
        if (!msg.from?.isLocal) {
          // Match by message text first, then by timestamp (within 3 seconds)
          const optionsEntry = Array.from(optionsMap.entries()).find(([key, value]) => {
            if (usedOptionsRef.current.has(key)) return false; // Skip already used options
            const entry = value as any;
            // Try matching by message text first
            if (entry.messageText && msg.message.toLowerCase().includes(entry.messageText.toLowerCase().substring(0, 20))) {
              return true;
            }
            // Fallback to timestamp matching
            const keyTime = parseInt(key.split('_').pop() || '0');
            const timeDiff = Math.abs(msg.timestamp - keyTime);
            return timeDiff < 3000; // Within 3 seconds
          });
          
          if (optionsEntry) {
            const [key, value] = optionsEntry;
            const entry = value as any;
            msg.options = entry.options || entry;
            // Mark as used
            usedOptionsRef.current.add(key);
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
