'use client';

import * as React from 'react';
import { cn } from '@/lib/utils';
import { Button } from '@/components/livekit/button';

export interface ChatOption {
  label: string;
  value: string;
}

export interface ChatOptionsProps extends React.HTMLAttributes<HTMLDivElement> {
  options: ChatOption[];
  onSelect: (value: string) => void;
  messageOrigin: 'local' | 'remote';
}

export const ChatOptions = ({
  options,
  onSelect,
  messageOrigin,
  className,
  ...props
}: ChatOptionsProps) => {
  if (!options || options.length === 0) return null;

  return (
    <div
      className={cn(
        'mt-2 flex flex-wrap gap-2',
        messageOrigin === 'local' ? 'justify-end' : 'justify-start',
        className
      )}
      {...props}
    >
      {options.map((option, index) => (
        <Button
          key={index}
          variant="outline"
          size="sm"
          onClick={() => onSelect(option.value)}
          className={cn(
            'text-xs',
            messageOrigin === 'local'
              ? 'bg-muted hover:bg-muted/80'
              : 'bg-primary/10 hover:bg-primary/20'
          )}
        >
          {option.label}
        </Button>
      ))}
    </div>
  );
};

