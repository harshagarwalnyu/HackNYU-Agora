// @vitest-environment jsdom
import { vi, describe, it, expect, beforeEach } from 'vitest';
import { renderHook } from '@testing-library/react';
import { useWebSocket } from './use-ws';
import { wsClient } from '@/lib/services/ws-client';
import { audioPlayer } from '@/lib/services/audio-player';

// Mock wsClient
vi.mock('@/lib/services/ws-client', () => {
  const mockConnect = vi.fn().mockResolvedValue(undefined);
  const mockDisconnect = vi.fn();
  const mockOn = vi.fn();
  const mockOff = vi.fn();
  const mockIsConnected = vi.fn().mockReturnValue(false);
  const mockSend = vi.fn();
  const mockSendAudio = vi.fn();
  const mockSendImage = vi.fn();
  const mockSendText = vi.fn();

  return {
    wsClient: {
      connect: mockConnect,
      disconnect: mockDisconnect,
      on: mockOn,
      off: mockOff,
      isConnected: mockIsConnected,
      send: mockSend,
      sendAudio: mockSendAudio,
      sendImage: mockSendImage,
      sendText: mockSendText,
    }
  };
});

// Mock audioPlayer
vi.mock('@/lib/services/audio-player', () => {
  const mockPlay = vi.fn();
  const mockStop = vi.fn();
  return {
    audioPlayer: {
      play: mockPlay,
      stop: mockStop,
    }
  };
});

// Mock Session Store
vi.mock('@/lib/store/session', () => {
  const mockSessionState = {
    userId: 'test-user',
    sessionId: 'test-session',
    currentTopic: 'test-topic',
    initSession: vi.fn(),
    isTutorAudioEnabled: true,
  };
  const mockGetSessionState = vi.fn(() => mockSessionState);

  return {
    useSessionStore: Object.assign(
      () => mockSessionState,
      {
        getState: mockGetSessionState
      }
    )
  };
});

// Mock Message Store
vi.mock('@/lib/store/messages', () => {
  const mockAddMessage = vi.fn();
  const mockSetLoading = vi.fn();
  const mockMessageState = {
    addMessage: mockAddMessage,
    setLoading: mockSetLoading,
  };
  const mockGetMessageState = vi.fn(() => mockMessageState);

  return {
    useMessageStore: Object.assign(
      () => mockMessageState,
      {
        getState: mockGetMessageState
      }
    )
  };
});

describe('useWebSocket', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should connect when userId and sessionId are present', async () => {
    renderHook(() => useWebSocket());

    // Wait a bit for the async effect
    await new Promise((resolve) => setTimeout(resolve, 0));

    expect(wsClient.connect).toHaveBeenCalledWith(expect.objectContaining({
      userId: 'test-user',
      sessionId: 'test-session',
    }));

    // Check that listeners are registered
    expect(wsClient.on).toHaveBeenCalledWith('connect', expect.any(Function));
    expect(wsClient.on).toHaveBeenCalledWith('session_initialized', expect.any(Function));
    expect(wsClient.on).toHaveBeenCalledWith('transcript', expect.any(Function));
    expect(wsClient.on).toHaveBeenCalledWith('audio_response', expect.any(Function));
    expect(wsClient.on).toHaveBeenCalledWith('visual', expect.any(Function));
    expect(wsClient.on).toHaveBeenCalledWith('session_status', expect.any(Function));
    expect(wsClient.on).toHaveBeenCalledWith('connection_status', expect.any(Function));
    expect(wsClient.on).toHaveBeenCalledWith('error', expect.any(Function));
  });

  it('should use stable callbacks (no re-connect on re-render)', async () => {
    const { rerender } = renderHook(() => useWebSocket());

    await new Promise((resolve) => setTimeout(resolve, 0));

    expect(wsClient.connect).toHaveBeenCalledTimes(1);
    const onCalls = (wsClient.on as any).mock.calls.length;

    // Rerender
    rerender();

    // Should not reconnect
    expect(wsClient.connect).toHaveBeenCalledTimes(1);

    // Should not re-register listeners
    expect(wsClient.on).toHaveBeenCalledTimes(onCalls);
  });

  it('should cleanup on unmount', async () => {
    const { unmount } = renderHook(() => useWebSocket());

    await new Promise((resolve) => setTimeout(resolve, 0));

    unmount();

    expect(wsClient.disconnect).toHaveBeenCalled();
    expect(audioPlayer.stop).toHaveBeenCalled();

    // Check that listeners are removed
    expect(wsClient.off).toHaveBeenCalledWith('connect', expect.any(Function));
    expect(wsClient.off).toHaveBeenCalledWith('session_initialized', expect.any(Function));
    expect(wsClient.off).toHaveBeenCalledWith('transcript', expect.any(Function));
    expect(wsClient.off).toHaveBeenCalledWith('audio_response', expect.any(Function));
    expect(wsClient.off).toHaveBeenCalledWith('visual', expect.any(Function));
    expect(wsClient.off).toHaveBeenCalledWith('session_status', expect.any(Function));
    expect(wsClient.off).toHaveBeenCalledWith('connection_status', expect.any(Function));
    expect(wsClient.off).toHaveBeenCalledWith('error', expect.any(Function));
  });
});
