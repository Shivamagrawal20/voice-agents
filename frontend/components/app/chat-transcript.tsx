'use client';

import { AnimatePresence, type HTMLMotionProps, motion } from 'motion/react';
import { type ReceivedChatMessage } from '@livekit/components-react';
import { useChat } from '@livekit/components-react';
import { ChatEntry } from '@/components/livekit/chat-entry';
import type { ChatOption } from '@/components/livekit/chat-options';

const MotionContainer = motion.create('div');
const MotionChatEntry = motion.create(ChatEntry);

interface ExtendedChatMessage extends ReceivedChatMessage {
  options?: ChatOption[];
}

const CONTAINER_MOTION_PROPS = {
  variants: {
    hidden: {
      opacity: 0,
      transition: {
        ease: 'easeOut',
        duration: 0.3,
        staggerChildren: 0.1,
        staggerDirection: -1,
      },
    },
    visible: {
      opacity: 1,
      transition: {
        delay: 0.2,
        ease: 'easeOut',
        duration: 0.3,
        stagerDelay: 0.2,
        staggerChildren: 0.1,
        staggerDirection: 1,
      },
    },
  },
  initial: 'hidden',
  animate: 'visible',
  exit: 'hidden',
};

const MESSAGE_MOTION_PROPS = {
  variants: {
    hidden: {
      opacity: 0,
      translateY: 10,
    },
    visible: {
      opacity: 1,
      translateY: 0,
    },
  },
};

interface ChatTranscriptProps {
  hidden?: boolean;
  messages?: ExtendedChatMessage[];
}

export function ChatTranscript({
  hidden = false,
  messages = [],
  ...props
}: ChatTranscriptProps & Omit<HTMLMotionProps<'div'>, 'ref'>) {
  const { send } = useChat();

  const handleOptionSelect = async (value: string) => {
    // Send the selected option as a chat message
    await send(value);
  };

  return (
    <AnimatePresence>
      {!hidden && (
        <MotionContainer {...CONTAINER_MOTION_PROPS} {...props}>
          {messages.map(({ id, timestamp, from, message, editTimestamp, options }: ExtendedChatMessage) => {
            const locale = navigator?.language ?? 'en-US';
            const messageOrigin = from?.isLocal ? 'local' : 'remote';
            const hasBeenEdited = !!editTimestamp;

            return (
              <MotionChatEntry
                key={id}
                locale={locale}
                timestamp={timestamp}
                message={message}
                messageOrigin={messageOrigin}
                hasBeenEdited={hasBeenEdited}
                options={options}
                onOptionSelect={handleOptionSelect}
                {...MESSAGE_MOTION_PROPS}
              />
            );
          })}
        </MotionContainer>
      )}
    </AnimatePresence>
  );
}
