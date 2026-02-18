export const API_CONFIG = {
    BASE_URL: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000',
    WS_URL: process.env.NEXT_PUBLIC_WS_URL || 'http://localhost:8000',
    TIMEOUTS: {
        WS_CONNECTION: 20000 as number,
        AUDIO_UPLOAD: 30000 as number,
        POLLING_INTERVAL: 2000 as number,
    },
} as const;

export const APP_CONFIG = {
    DEFAULT_TOPIC: 'General',
    FILE_LIMITS: {
        MAX_SIZE: (50 * 1024 * 1024) as number, // 50MB
        ALLOWED_TYPES: [
            'application/pdf',
            'text/plain',
            'image/png',
            'image/jpeg',
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            'application/vnd.openxmlformats-officedocument.presentationml.presentation',
        ],
    },
    AUDIO: {
        SAMPLE_RATE: 16000,
        BIT_RATE: 128000,
        MIME_TYPE: 'audio/webm',
    }
} as const;
