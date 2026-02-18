import { io, Socket } from 'socket.io-client';
import { API_CONFIG } from '../constants';
import { blobToBase64 } from '../utils/encoding';

interface WSClientConfig {
  url: string;
  userId: string;
  sessionId: string;
}

type MessageCallback = (message: Record<string, unknown>) => void;

export class WSClient {
  private socket: Socket | null = null;
  private config: WSClientConfig | null = null;
  private callbacks: Map<string, MessageCallback[]> = new Map();
  private maxReconnectAttempts = 5;

  async connect(config: WSClientConfig): Promise<void> {
    this.config = config;

    return new Promise((resolve, reject) => {
      try {
        console.log('[Agora] Creating Socket.IO connection to:', config.url);

        this.socket = io(config.url, {
          reconnection: true,
          reconnectionDelay: 1000,
          reconnectionDelayMax: 5000,
          reconnectionAttempts: this.maxReconnectAttempts,
          transports: ['websocket', 'polling'],
          upgrade: true,
          rememberUpgrade: true,
          query: {
            user_id: config.userId,
            session_id: config.sessionId,
          },
          timeout: API_CONFIG.TIMEOUTS.WS_CONNECTION,
        });

        // Set up timeout
        const timeout = setTimeout(() => {
          if (!this.socket?.connected) {
            console.error('[Agora] Connection timeout');
            reject(new Error('WebSocket connection timeout'));
          }
        }, API_CONFIG.TIMEOUTS.WS_CONNECTION);

        // Connection successful
        this.socket.on('connect', () => {
          console.log('[Agora] WebSocket connected, socket ID:', this.socket?.id);
          clearTimeout(timeout);
          // Emit internal event for tracking
          this.emit('connect', {});
          this.emit('connection_status', { connected: true });
          resolve();
        });

        // Connection failed
        this.socket.on('connect_error', (error) => {
          console.error('[Agora] Connection error:', error);
          clearTimeout(timeout);
          this.emit('error', { message: error.message || 'Connection failed' });
          if (!this.socket?.connected) reject(error);
        });

        this.socket.on('disconnect', (reason) => {
          console.log('[Agora] WebSocket disconnected:', reason);
          this.emit('connection_status', { connected: false });
        });

        this.socket.on('error', (data) => {
          const message = (typeof data === 'object' && data?.message) ? data.message : String(data);
          console.error(`[Agora] WebSocket Error: ${message} `, data);
          this.emit('error', { message });
        });

        // Set up message handlers
        const eventNames = [
          'transcript',
          'audio_response',
          'visual',
          'session_status',
          'session_initialized',
        ];

        eventNames.forEach((event) => {
          this.socket?.on(event, (data) => this.emit(event, data));
        });

        // Log connection attempts
        this.socket.on('connecting', () => console.log('[Agora] Connecting...'));

      } catch (error) {
        console.error('[Agora] Failed to create socket:', error);
        reject(error);
      }
    });
  }

  disconnect(): void {
    if (this.socket) {
      this.socket.disconnect();
      this.socket = null;
    }
  }

  async sendAudio(blob: Blob): Promise<void> {
    if (!this.socket || !this.config) throw new Error('WebSocket not connected');

    try {
      const base64 = await blobToBase64(blob);
      this.socket.emit('audio_input', {
        type: 'audio_input',
        session_id: this.config.sessionId,
        user_id: this.config.userId,
        format: 'audio/webm',
        data: base64,
      });
    } catch (error) {
      console.error('[Agora] Failed to send audio:', error);
      throw error;
    }
  }

  async sendImage(blob: Blob): Promise<void> {
    if (!this.socket || !this.config) throw new Error('WebSocket not connected');

    try {
      const base64 = await blobToBase64(blob);
      this.socket.emit('visual_input', {
        type: 'visual_input',
        session_id: this.config.sessionId,
        user_id: this.config.userId,
        image: base64,
      });
    } catch (error) {
      console.error('[Agora] Failed to send image:', error);
      throw error;
    }
  }

  sendText(text: string): void {
    if (!this.socket || !this.config) throw new Error('WebSocket not connected');

    this.socket.emit('text_input', {
      type: 'text_input',
      session_id: this.config.sessionId,
      user_id: this.config.userId,
      text,
    });
  }

  send(event: string, data: Record<string, unknown>): void {
    if (!this.socket) throw new Error('WebSocket not connected');

    this.socket.emit(event, data);
  }

  on(messageType: string, callback: MessageCallback): void {
    if (!this.callbacks.has(messageType)) {
      this.callbacks.set(messageType, []);
    }
    this.callbacks.get(messageType)?.push(callback);
  }

  off(messageType: string, callback: MessageCallback): void {
    const callbacks = this.callbacks.get(messageType);
    if (callbacks) {
      const index = callbacks.indexOf(callback);
      if (index > -1) callbacks.splice(index, 1);
    }
  }

  private emit(messageType: string, data: Record<string, unknown>): void {
    this.callbacks.get(messageType)?.forEach((cb) => cb(data));
  }

  isConnected(): boolean {
    return this.socket?.connected ?? false;
  }
}

export const wsClient = new WSClient();
