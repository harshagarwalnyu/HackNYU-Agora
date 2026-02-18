import { useEffect, useState, useCallback } from 'react';
import { wsClient } from '@/lib/services/ws-client';
import { audioPlayer } from '@/lib/services/audio-player';
import { useSessionStore } from '@/lib/store/session';
import { useMessageStore } from '@/lib/store/messages';
import { APP_CONFIG, API_CONFIG } from '@/lib/constants';
import {
  TranscriptMessage,
  AudioResponseMessage,
  VisualAction,
  SessionStatus,
  ConnectionStatus,
  ErrorMessage,
  SessionInitialized
} from '@/lib/types';

// Debug logging helper - only logs in development
const debugLog = (message: string, data?: unknown) => {
  if (process.env.NODE_ENV === 'development') {
    console.log(`[Agora] ${message}`, data ?? '');
  }
};

const debugError = (message: string, error?: unknown) => {
  if (process.env.NODE_ENV === 'development') {
    console.error(`[Agora] ${message}`, error ?? '');
  }
};

export function useWebSocket() {
  const [isReady, setIsReady] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const { userId, sessionId, currentTopic } = useSessionStore();
  const { setLoading } = useMessageStore();

  const onSessionInitialized = useCallback((data: SessionInitialized) => {
    debugLog('Session initialized:', data);
    setIsReady(true);
  }, []);

  const onTranscript = useCallback((data: TranscriptMessage) => {
    debugLog('Transcript received:', data);
    useMessageStore.getState().addMessage(data.from, data.text);
    useMessageStore.getState().setLoading(false);
  }, []);

  const onAudioResponse = useCallback((data: AudioResponseMessage) => {
    debugLog('Audio response received');
    if (useSessionStore.getState().isTutorAudioEnabled) {
      const audioData = `data:${data.format};base64,${data.data}`;
      audioPlayer.play(audioData);
    } else {
      debugLog('Audio playback skipped (tutor is muted)');
    }
  }, []);

  const onVisual = useCallback((data: VisualAction) => {
    debugLog('Visual action received:', data);
    window.dispatchEvent(new CustomEvent('agora:visual', { detail: data }));
  }, []);

  const onSessionStatus = useCallback((data: SessionStatus) => {
    debugLog('Session status:', data);
    const terminalStates: SessionStatus['status'][] = ['complete', 'interrupted', 'cancelled'];
    if (terminalStates.includes(data.status)) {
      useMessageStore.getState().setLoading(false);
    }
  }, []);

  const onConnectionStatus = useCallback((data: ConnectionStatus) => {
    debugLog('Connection status:', data);
    setIsReady(data.connected);
  }, []);

  const onError = useCallback((data: ErrorMessage) => {
    setError(data.message);
    debugError('WebSocket error:', data);
    useMessageStore.getState().setLoading(false);
    setIsReady(false);
  }, []);

  const onConnect = useCallback(() => {
    try {
      debugLog('Socket.IO connected!');
      const state = useSessionStore.getState();
      if (!state) {
        debugError('Session store state is missing');
        return;
      }

      wsClient.send('init_session', {
        user_id: state.userId,
        session_id: state.sessionId,
        course_id: state.currentTopic || APP_CONFIG.DEFAULT_TOPIC
      });
    } catch (error) {
      debugError('Error in onConnect:', error);
    }
  }, []);

  useEffect(() => {
    let isMounted = true;
    const handlers = {
      connect: onConnect,
      session_initialized: onSessionInitialized,
      transcript: onTranscript,
      audio_response: onAudioResponse,
      visual: onVisual,
      session_status: onSessionStatus,
      connection_status: onConnectionStatus,
      error: onError,
    };

    const setupConnection = async () => {
      try {
        const wsUrl = API_CONFIG.WS_URL;
        debugLog('Connecting to WebSocket:', wsUrl);

        Object.entries(handlers).forEach(([event, handler]) => {
          wsClient.on(event, handler as (message: Record<string, unknown>) => void);
        });

        await wsClient.connect({ url: wsUrl, userId, sessionId });
      } catch (err) {
        if (!isMounted) return;
        setError(err instanceof Error ? err.message : 'Connection failed');
        debugError('WebSocket setup failed:', err);
        setIsReady(false);
      }
    };

    if (userId && sessionId) {
      setupConnection();
    }

    return () => {
      isMounted = false;
      debugLog('Cleaning up WebSocket listeners...');
      Object.entries(handlers).forEach(([event, handler]) => {
        wsClient.off(event, handler as (message: Record<string, unknown>) => void);
      });
      wsClient.disconnect();
      audioPlayer.stop();
    };
  }, [userId, sessionId, onConnect, onSessionInitialized, onTranscript, onAudioResponse, onVisual, onSessionStatus, onConnectionStatus, onError]);


  const interrupt = useCallback(() => {
    audioPlayer.stop();
    try {
      wsClient.send('interrupt', {});
    } catch (e) {
      // Ignore if not connected
    }
  }, []);

  const sendAudio = useCallback(
    async (blob: Blob) => {
      if (!isReady) {
        setError('WebSocket not ready');
        return;
      }
      try {
        interrupt(); // Stop current playback and processing
        setLoading(true);
        await wsClient.sendAudio(blob);
      } catch (err) {
        const message = err instanceof Error ? err.message : 'Failed to send audio';
        setError(message);
        setLoading(false);
      }
    },
    [isReady, setLoading, interrupt]
  );

  const sendImage = useCallback(
    async (blob: Blob) => {
      if (!isReady) {
        setError('WebSocket not ready');
        return;
      }
      try {
        interrupt();
        setLoading(true);
        await wsClient.sendImage(blob);
      } catch (err) {
        const message = err instanceof Error ? err.message : 'Failed to send image';
        setError(message);
        setLoading(false);
      }
    },
    [isReady, setLoading, interrupt]
  );

  const sendText = useCallback(
    (text: string) => {
      if (!isReady) {
        setError('WebSocket not ready');
        return;
      }
      try {
        interrupt();
        wsClient.sendText(text);
      } catch (err) {
        const message = err instanceof Error ? err.message : 'Failed to send text';
        setError(message);
      }
    },
    [isReady, interrupt]
  );

  return {
    isReady,
    error,
    sendAudio,
    sendText,
    sendImage,
    interrupt,
    isConnected: wsClient.isConnected(),
  };
}
