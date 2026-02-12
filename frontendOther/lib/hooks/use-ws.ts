import { useEffect, useState, useCallback } from 'react';
import { wsClient } from '@/lib/services/ws-client';
import { audioPlayer } from '@/lib/services/audio-player';
import { useSessionStore } from '@/lib/store/session';
import { useMessageStore } from '@/lib/store/messages';

export function useWebSocket() {
  const [isReady, setIsReady] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const { userId, sessionId, initSession, currentTopic } = useSessionStore();
  const { addMessage, setLoading } = useMessageStore();

  // FIX: Define stable callbacks using useCallback
  // This ensures they have a stable reference and can be added/removed.
  // We use getState() inside to avoid adding store functions as dependencies.

  const onSessionInitialized = useCallback((data: any) => {
    console.log('[Agora] Session initialized:', data);
    setIsReady(true);
  }, []); // No dependencies needed

  const onTranscript = useCallback((data: any) => {
    console.log('[Agora] Transcript received:', data);
    // Use getState() to get the latest functions without causing re-renders
    useMessageStore.getState().addMessage(data.from, data.text);
    useMessageStore.getState().setLoading(false);
  }, []); // No dependencies needed

  const onAudioResponse = useCallback((data: any) => {
    console.log('[Agora] Audio response received');
    if (useSessionStore.getState().isTutorAudioEnabled) {
      const audioData = `data:${data.format};base64,${data.data}`;
      audioPlayer.play(audioData);
    } else {
      console.log('[Agora] Audio playback skipped (tutor is muted)');
    }
  }, []); // No dependencies needed

  const onVisual = useCallback((data: any) => {
    console.log('[Agora] Visual action received:', data);
    window.dispatchEvent(new CustomEvent('agora:visual', { detail: data }));
  }, []); // No dependencies needed

  const onSessionStatus = useCallback((data: any) => {
    console.log('[Agora] Session status:', data);
    if (data.status === 'complete' || data.status === 'interrupted' || data.status === 'cancelled') {
      useMessageStore.getState().setLoading(false);
    }
  }, []); // No dependencies needed

  const onConnectionStatus = useCallback((data: any) => {
    console.log('[Agora] Connection status:', data);
    setIsReady(data.connected);
  }, []); // No dependencies needed

  const onError = useCallback((data: any) => {
    setError(data.message);
    console.error('[Agora] WebSocket error:', data);
    useMessageStore.getState().setLoading(false);
    setIsReady(false);
  }, []); // No dependencies needed

  const onConnect = useCallback(() => {
    try {
      console.log('[Agora] Socket.IO connected! Socket ID:', wsClient.isConnected());

      const state = useSessionStore.getState();
      if (!state) {
        console.error('[Agora] Session store state is missing');
        return;
      }

      console.log('[Agora] Sending init_session...');
      wsClient.send('init_session', {
        user_id: state.userId,
        session_id: state.sessionId,
        course_id: state.currentTopic || 'General'
      });
    } catch (error) {
      console.error('[Agora] Error in onConnect:', error);
    }
  }, []); // No dependencies needed


  useEffect(() => {
    const setupConnection = async () => {
      try {
        const wsUrl = process.env.NEXT_PUBLIC_WS_URL || 'http://localhost:8000';
        console.log('[Agora] Connecting to WebSocket:', wsUrl);

        // Setup connect handler BEFORE connecting
        wsClient.on('connect', onConnect);

        await wsClient.connect({
          url: wsUrl,
          userId,
          sessionId,
        });

        // ** FIX: Register the stable callbacks **
        wsClient.on('session_initialized', onSessionInitialized);
        wsClient.on('transcript', onTranscript);
        wsClient.on('audio_response', onAudioResponse);
        wsClient.on('visual', onVisual);
        wsClient.on('session_status', onSessionStatus);
        wsClient.on('connection_status', onConnectionStatus);
        wsClient.on('error', onError);

      } catch (err) {
        const message = err instanceof Error ? err.message : 'Connection failed';
        setError(message);
        console.error('[Agora] WebSocket setup failed:', err);
        setIsReady(false);
      }
    };

    if (userId && sessionId) {
      setupConnection();
    }

    // ** FIX: The Correct Cleanup Function **
    return () => {
      console.log('[Agora] Cleaning up WebSocket listeners...');
      // ** Un-register the listeners to prevent leaks **
      // Note: Cannot remove 'connect' handler without storing its reference
      wsClient.off('connect', onConnect);
      wsClient.off('session_initialized', onSessionInitialized);
      wsClient.off('transcript', onTranscript);
      wsClient.off('audio_response', onAudioResponse);
      wsClient.off('visual', onVisual);
      wsClient.off('session_status', onSessionStatus);
      wsClient.off('connection_status', onConnectionStatus);
      wsClient.off('error', onError);

      wsClient.disconnect();
      audioPlayer.stop();
    };
    // ** FIX: Update dependency array **
    // We only want this effect to run when the session IDs change, not when
    // state setters from Zustand change.
  }, [userId, sessionId, currentTopic,
    onSessionInitialized, onTranscript, onAudioResponse, onVisual,
    onSessionStatus, onConnectionStatus, onError, onConnect]);


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