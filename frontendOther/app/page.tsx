'use client';

import { useEffect, useRef, useState } from 'react';
import { OrbStatus } from '@/components/orb-status';
import { RecorderButton } from '@/components/recorder-button';
import { TranscriptPanel } from '@/components/transcript-panel';
import { WhiteboardPane } from '@/components/whiteboard-pane';
import { SessionSidebar } from '@/components/session-sidebar';
import { useWebSocket } from '@/lib/hooks/use-ws';
import { useMessageStore } from '@/lib/store/messages';
import { useSessionStore } from '@/lib/store/session';

type OrbState = 'idle' | 'listening' | 'thinking' | 'speaking';

export default function AgoraPage() {
  const whiteboardRef = useRef<any>(null);
  const [orbState, setOrbState] = useState<OrbState>('idle');
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [textInput, setTextInput] = useState('');
  const { isReady, sendAudio, sendText, isConnected } = useWebSocket();
  const { messages, isLoading, addMessage } = useMessageStore();
  const { initSession, isTutorAudioEnabled, toggleTutorAudio } = useSessionStore();

  useEffect(() => {
    initSession();
  }, [initSession]);

  useEffect(() => {
    const handleVisualAction = (event: Event) => {
      const customEvent = event as CustomEvent;
      const action = customEvent.detail;

      if (whiteboardRef.current) {
        switch (action.action) {
          case 'CREATE_NOTE':
            whiteboardRef.current.addNote?.(
              action.payload.text,
              action.payload.x,
              action.payload.y
            );
            break;
          case 'LOAD_IMAGE':
            whiteboardRef.current.addImage?.(
              action.payload.imageSrc,
              action.payload.x,
              action.payload.y
            );
            break;
          case 'CLEAR_BOARD':
            whiteboardRef.current.clear?.();
            break;
        }
      }
    };

    window.addEventListener('agora:visual', handleVisualAction);
    return () => window.removeEventListener('agora:visual', handleVisualAction);
  }, []);

  const handleAudioSubmit = async (blob: Blob) => {
    if (!isReady) {
      console.error('[Agora] WebSocket not ready');
      return;
    }

    try {
      setOrbState('thinking');
      // addMessage('student', 'Recording...');
      await sendAudio(blob);
    } catch (error) {
      console.error('[Agora] Failed to send audio:', error);
      setOrbState('idle');
    }
  };

  const handleTextSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!isReady || !textInput.trim()) {
      return;
    }

    try {
      setOrbState('thinking');
      addMessage('student', textInput);
      await sendText(textInput);
      setTextInput('');
    } catch (error) {
      console.error('[Agora] Failed to send text:', error);
      setOrbState('idle');
    }
  };

  useEffect(() => {
    if (isLoading) {
      setOrbState('thinking');
    } else {
      setOrbState('idle');
    }
  }, [isLoading]);

  return (
    <main className="flex h-screen w-full bg-zinc-950 overflow-hidden">
      <div className="flex-1 flex flex-col">
        {/* Header with Orb */}
        <header className="flex-shrink-0 px-8 py-4 border-b border-zinc-800 bg-black">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-6">
              <div>
                <h1 className="text-3xl font-bold text-white">Agora</h1>
                <p className="text-xs text-zinc-400 mt-0.5">
                  {isConnected ? 'Connected' : 'Connecting...'}
                </p>
              </div>
              {/* Orb moved to header */}
              <div className="ml-4">
                <OrbStatus state={orbState} />
              </div>
            </div>
            <div className="flex items-center gap-3">
              <span
                className={`text-xs font-semibold uppercase tracking-wider px-3 py-1 rounded-full ${isConnected
                    ? 'bg-green-500/10 text-green-400 border border-green-500/30'
                    : 'bg-yellow-500/10 text-yellow-400 border border-yellow-500/30'
                  }`}
              >
                {isConnected ? '● Ready' : '○ Connecting'}
              </span>
              <button
                onClick={toggleTutorAudio}
                title={isTutorAudioEnabled ? 'Mute Tutor Voice' : 'Unmute Tutor Voice'}
                className="p-2 rounded-lg text-zinc-400 hover:text-white hover:bg-zinc-800 transition-colors"
              >
                {isTutorAudioEnabled ? (
                  <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"></polygon><path d="M15.54 8.46a5 5 0 0 1 0 7.07"></path></svg>
                ) : (
                  <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"></polygon><line x1="23" y1="9" x2="17" y2="15"></line><line x1="17" y1="9" x2="23" y2="15"></line></svg>
                )}
              </button>
            </div>
          </div>
        </header>

        {/* Main content area */}
        <div className="flex-1 flex overflow-hidden min-h-0">
          {/* Blackboard (before Whiteboard) */}
          <div className="flex-1 flex flex-col min-w-0 min-h-0 bg-zinc-900">
            <WhiteboardPane ref={whiteboardRef} />
          </div>

          {/* Conversation - Responsive width */}
          <div className="w-full sm:w-[400px] md:w-[450px] lg:w-[500px] xl:w-[600px] flex flex-col border-l border-zinc-800 flex-shrink-0 bg-black">
            <TranscriptPanel messages={messages} isLoading={isLoading} />
          </div>
        </div>

        {/* Bottom control panel */}
        <div className="flex-shrink-0 flex flex-col items-center justify-center py-4 px-6 bg-black border-t border-zinc-800 gap-4">
          <div className="flex items-center gap-4 w-full max-w-4xl">
            <RecorderButton
              onAudioSubmit={handleAudioSubmit}
              disabled={!isReady}
              isProcessing={isLoading}
            />

            <form onSubmit={handleTextSubmit} className="flex-1 flex gap-2">
              <input
                type="text"
                value={textInput}
                onChange={(e) => setTextInput(e.target.value)}
                placeholder="Ask your tutor anything..."
                disabled={!isReady || isLoading}
                className="flex-1 px-5 py-3 rounded-lg border border-zinc-700 bg-zinc-900 text-white placeholder:text-zinc-500 disabled:opacity-50 disabled:cursor-not-allowed focus:outline-none focus:ring-2 focus:ring-zinc-600 focus:border-zinc-600 transition-all"
                autoComplete="off"
              />
              <button
                type="submit"
                disabled={!isReady || isLoading || !textInput.trim()}
                className="px-8 py-3 rounded-lg bg-zinc-800 text-white font-semibold hover:bg-zinc-700 disabled:opacity-50 disabled:cursor-not-allowed transition-all focus:outline-none focus:ring-2 focus:ring-zinc-600"
              >
                Send
              </button>
            </form>
          </div>

          <p className="text-xs text-zinc-500 text-center">
            {orbState === 'idle' && 'Hold to speak, or type your question above'}
            {orbState === 'listening' && 'Listening to your question...'}
            {orbState === 'thinking' && 'Tutor is thinking...'}
            {orbState === 'speaking' && 'Tutor is responding...'}
          </p>
        </div>
      </div>

      <SessionSidebar
        isCollapsed={sidebarCollapsed}
        onToggle={setSidebarCollapsed}
      />
    </main>
  );
}
