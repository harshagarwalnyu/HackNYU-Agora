import { io, Socket } from 'socket.io-client';

interface WSClientConfig {
  url: string;
  userId: string;
  sessionId: string;
}

type MessageCallback = (message: any) => void;

export class WSClient {
  private socket: Socket | null = null;
  private config: WSClientConfig | null = null;
  private callbacks: Map<string, MessageCallback[]> = new Map();
  private reconnectAttempts = 0;
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
          timeout: 20000,
        });

        // Set up timeout
        const timeout = setTimeout(() => {
          if (!this.socket?.connected) {
            console.error('[Agora] Connection timeout after 20s');
            reject(new Error('WebSocket connection timeout'));
          }
        }, 20000);

        // Connection successful
        this.socket.on('connect', () => {
          console.log('[Agora] WebSocket connected, socket ID:', this.socket?.id);
          clearTimeout(timeout);
          this.reconnectAttempts = 0;
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
          if (!this.socket?.connected) {
            reject(error);
          }
        });

        this.socket.on('disconnect', (reason) => {
          console.log('[Agora] WebSocket disconnected:', reason);
          this.emit('connection_status', { connected: false });
        });

        // this.socket.on('error', (error) => {
        //   console.error('[Agora] WebSocket error:', error);
        //   this.emit('error', { message: error });
        // });

        this.socket.on('error', (data) => {
          // This handles errors sent from the backend OR transport errors
          let errorMessage = 'Unknown WebSocket error';

          if (typeof data === 'object' && data !== null && data.message) {
            // This is the expected format: { message: "..." }
            errorMessage = data.message;
          } else if (typeof data === 'string' && data.trim() !== '{}') {
            // This handles if the error is just a string
            errorMessage = data;
          } else if (data) {
            // This is a fallback for weird objects like {}
            try {
              errorMessage = `Received error object: ${JSON.stringify(data)}`;
            } catch {
              errorMessage = String(data);
            }
          }

          console.error(`[Agora] WebSocket Error Received: ${errorMessage}`, data);
          this.emit('error', { message: errorMessage });
        });

        // Set up message handlers
        this.socket.on('transcript', (data) => {
          this.emit('transcript', data);
        });

        this.socket.on('audio_response', (data) => {
          this.emit('audio_response', data);
        });

        this.socket.on('visual', (data) => {
          this.emit('visual', data);
        });

        this.socket.on('session_status', (data) => {
          this.emit('session_status', data);
        });

        this.socket.on('session_initialized', (data) => {
          this.emit('session_initialized', data);
        });

        // Log connection attempts
        this.socket.on('connecting', () => {
          console.log('[Agora] Connecting...');
        });

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
    if (!this.socket || !this.config) {
      throw new Error('WebSocket not connected');
    }

    try {
      const base64 = await this.blobToBase64(blob);
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
    if (!this.socket || !this.config) {
      throw new Error('WebSocket not connected');
    }

    try {
      const base64 = await this.blobToBase64(blob);
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
    if (!this.socket || !this.config) {
      throw new Error('WebSocket not connected');
    }

    this.socket.emit('text_input', {
      type: 'text_input',
      session_id: this.config.sessionId,
      user_id: this.config.userId,
      text,
    });
  }

  send(event: string, data: any): void {
    if (!this.socket) {
      throw new Error('WebSocket not connected');
    }

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
      if (index > -1) {
        callbacks.splice(index, 1);
      }
    }
  }

  private emit(messageType: string, data: any): void {
    const callbacks = this.callbacks.get(messageType);
    if (callbacks) {
      callbacks.forEach((cb) => cb(data));
    }
  }

  private blobToBase64(blob: Blob): Promise<string> {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onloadend = () => {
        const base64 = reader.result as string;
        resolve(base64.split(',')[1]);
      };
      reader.onerror = reject;
      reader.readAsDataURL(blob);
    });
  }

  isConnected(): boolean {
    return this.socket?.connected ?? false;
  }
}

export const wsClient = new WSClient();
