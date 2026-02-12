/**
 * Agora constants and configuration
 */

export const AGORA_CONFIG = {
  // Voice states
  ORB_STATES: ['idle', 'listening', 'thinking', 'speaking'] as const,
  
  // Timeouts (ms)
  WS_CONNECTION_TIMEOUT: 10000,
  AUDIO_UPLOAD_TIMEOUT: 30000,
  
  // Audio settings
  AUDIO_MIME_TYPE: 'audio/webm',
  AUDIO_BIT_RATE: 128000,
  AUDIO_SAMPLE_RATE: 16000,
  
  // UI settings
  MESSAGE_ANIMATION_DURATION: 300,
  ORB_PULSE_INTERVAL: 2000,
  AUTO_SCROLL_DELAY: 100,
  
  // File upload
  MAX_FILE_SIZE: 50 * 1024 * 1024, // 50MB
  ALLOWED_FILE_TYPES: [
    'application/pdf',
    'text/plain',
    'image/png',
    'image/jpeg',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
  ],
} as const;

export const AGORA_MESSAGES = {
  WELCOME: 'Hold the button and speak to ask a question',
  LISTENING: 'Listening to your question...',
  THINKING: 'Tutor is thinking...',
  SPEAKING: 'Tutor is responding...',
  CONNECTION_ERROR: 'Failed to connect to Agora. Please refresh.',
  UPLOAD_ERROR: 'Failed to upload file. Please try again.',
  AUDIO_ERROR: 'Microphone access denied. Please enable it in settings.',
} as const;
