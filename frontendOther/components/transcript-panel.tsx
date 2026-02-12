'use client';

import { useEffect, useRef } from 'react';

export interface Message {
  id: string;
  from: 'student' | 'tutor';
  text: string;
  timestamp: Date;
}

interface TranscriptPanelProps {
  messages: Message[];
  isLoading?: boolean;
  onScroll?: (position: number) => void;
}

export function TranscriptPanel({
  messages,
  isLoading = false,
  onScroll,
}: TranscriptPanelProps) {
  const scrollContainerRef = useRef<HTMLDivElement>(null);
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleScroll = () => {
    if (scrollContainerRef.current && onScroll) {
      onScroll(scrollContainerRef.current.scrollTop);
    }
  };

  return (
    <div className="flex flex-col h-full bg-black">
      <div className="flex-shrink-0 px-6 py-4 border-b border-zinc-800">
        <h3 className="text-xl font-bold text-white">Conversation</h3>
        <p className="text-xs text-zinc-500 mt-1">
          {messages.length} {messages.length === 1 ? 'message' : 'messages'}
        </p>
      </div>

      <div
        ref={scrollContainerRef}
        onScroll={handleScroll}
        className="flex-1 overflow-y-auto p-6 space-y-5"
      >
        {messages.length === 0 ? (
          <div className="flex items-center justify-center h-full text-center">
            <div className="p-8 rounded-lg bg-zinc-900 border border-zinc-800">
              <p className="text-white font-medium text-base">No messages yet</p>
              <p className="text-sm text-zinc-400 mt-3">
                Hold the mic button and speak<br />or type your question below
              </p>
            </div>
          </div>
        ) : (
          messages.map((msg) => (
            <div
              key={msg.id}
              className={`flex ${
                msg.from === 'student' ? 'justify-end' : 'justify-start'
              } animate-fade-in`}
            >
              <div
                className={`max-w-[85%] px-5 py-4 rounded-lg ${
                  msg.from === 'student'
                    ? 'bg-zinc-800 text-white border border-zinc-700'
                    : 'bg-zinc-900 text-zinc-100 border border-zinc-800'
                }`}
              >
                <p className="text-[15px] leading-relaxed whitespace-pre-wrap">{msg.text}</p>
                <p
                  className={`text-xs mt-2.5 ${
                    msg.from === 'student'
                      ? 'text-zinc-400'
                      : 'text-zinc-500'
                  }`}
                >
                  {msg.from === 'student' ? 'You' : 'Tutor'} • {msg.timestamp.toLocaleTimeString([], {
                    hour: '2-digit',
                    minute: '2-digit',
                  })}
                </p>
              </div>
            </div>
          ))
        )}

        {isLoading && (
          <div className="flex justify-start">
            <div className="bg-zinc-900 text-zinc-100 px-5 py-4 rounded-lg border border-zinc-800">
              <div className="flex gap-2 items-center">
                <div className="w-2.5 h-2.5 bg-zinc-600 rounded-full animate-pulse" />
                <div className="w-2.5 h-2.5 bg-zinc-600 rounded-full animate-pulse animation-delay-200" />
                <div className="w-2.5 h-2.5 bg-zinc-600 rounded-full animate-pulse animation-delay-400" />
              </div>
            </div>
          </div>
        )}

        <div ref={endRef} />
      </div>

      <div className="flex-shrink-0 px-6 py-3 border-t border-zinc-800 bg-zinc-950 text-xs text-zinc-600 text-center">
        Real-time transcription
      </div>
    </div>
  );
}
