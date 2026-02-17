import { renderHook } from '@testing-library/react';
import { useWebSocket } from './use-ws';
import { useSessionStore } from '@/lib/store/session';
import { wsClient } from '@/lib/services/ws-client';
import { vi, describe, it, expect, beforeEach, afterEach } from 'vitest';

// Mock wsClient
vi.mock('@/lib/services/ws-client', () => ({
  wsClient: {
    connect: vi.fn(),
    disconnect: vi.fn(),
    on: vi.fn(),
    off: vi.fn(),
    isConnected: vi.fn().mockReturnValue(false),
    send: vi.fn(),
    sendAudio: vi.fn(),
    sendImage: vi.fn(),
    sendText: vi.fn(),
  }
}));

// Mock audioPlayer
vi.mock('@/lib/services/audio-player', () => ({
  audioPlayer: {
    stop: vi.fn(),
    play: vi.fn(),
  }
}));

// Mock useSessionStore: we mock the module to control the returned values
// but we want to simulate state updates.
// Since useSessionStore is a hook exported from zustand store, we can just use it as is?
// But usually zustand persists state between tests unless reset.
// Let's reset it.

describe('useWebSocket', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    useSessionStore.setState({
      userId: 'test-user',
      sessionId: 'test-session',
      currentTopic: 'Math',
      isTutorAudioEnabled: true
    }, true); // true to replace state completely? No, setState merges by default unless true is passed for replacement (depends on zustand version/setup).
    // Actually, create<Store>() returns a hook that also has setState and getState.
    // The implementation of useSessionStore is:
    /*
    export const useSessionStore = create<SessionStore>((set) => ({ ... }));
    */
  });

  it('connects when userId and sessionId are present', () => {
    renderHook(() => useWebSocket());

    // Check if wsClient.connect was called
    expect(wsClient.connect).toHaveBeenCalledTimes(1);
    expect(wsClient.connect).toHaveBeenCalledWith(expect.objectContaining({
      userId: 'test-user',
      sessionId: 'test-session'
    }));
  });

  it('reconnects when sessionId changes', () => {
    const { rerender } = renderHook(() => useWebSocket());
    expect(wsClient.connect).toHaveBeenCalledTimes(1);

    // Update session ID
    useSessionStore.setState({ sessionId: 'new-session' });

    // Rerender hook (although store update triggers rerender)
    rerender();

    // Should have called connect again (total 2 times)
    expect(wsClient.connect).toHaveBeenCalledTimes(2);
    expect(wsClient.connect).toHaveBeenLastCalledWith(expect.objectContaining({
      sessionId: 'new-session'
    }));
  });

  it('does NOT reconnect when currentTopic changes', () => {
    const { rerender } = renderHook(() => useWebSocket());
    expect(wsClient.connect).toHaveBeenCalledTimes(1);

    // Update topic
    useSessionStore.setState({ currentTopic: 'Physics' });

    rerender();

    // Expect connect NOT to be called again
    expect(wsClient.connect).toHaveBeenCalledTimes(1);
  });
});
