# Agora Frontend - Voice-First Socratic Tutor

A voice-first AI tutoring system.

## Architecture Overview

### Components
- **OrbStatus**: Animated voice state indicator (idle, listening, thinking, speaking)
- **RecorderButton**: Push-to-talk voice recording interface
- **TranscriptPanel**: Real-time conversation display with smooth animations
- **WhiteboardPane**: Canvas-based collaborative whiteboard for visual explanations
- **SessionSidebar**: Materials upload and settings management
- **UploadPanel**: Drag-and-drop file upload interface

### Services
- **WSClient**: WebSocket connection management with automatic reconnection
- **AudioRecorder**: Browser MediaRecorder wrapper with audio encoding

### State Management
- **useMessageStore**: Zustand store for conversation messages
- **useSessionStore**: Zustand store for user session and materials
- **useWebSocket**: Custom hook for WebSocket lifecycle and message handling

## Getting Started

### 1. Install Dependencies

\`\`\`bash
npm install
# or
pnpm install
\`\`\`

### 2. Environment Setup

Create `.env.local`:

\`\`\`bash
NEXT_PUBLIC_WS_URL=ws://localhost:8000/api/ws/connect
NEXT_PUBLIC_API_URL=http://localhost:8000
\`\`\`

### 3. Run Development Server

\`\`\`bash
npm run dev
# or
pnpm dev
\`\`\`

Open [http://localhost:3000](http://localhost:3000) in your browser.

## Design System

### Color Palette (Nike-Inspired)
- **Primary Black**: `#111111` - Main text and structure
- **Primary Light Gray**: `#757575` - Secondary text
- **Secondary White**: `#FFFFFF` - Backgrounds
- **Secondary Dark Gray**: `#F5F5F5` - Subtle backgrounds
- **Accent Orange**: `#FF6B00` - Actions and highlights

### Typography
- **Font Family**: Inter (system-ui fallback)
- **Headings**: Bold, uppercase, wide tracking
- **Body**: Regular weight, generous line-height
- **Sizes**: Large for impact, small for details

### Animation System
- **Fade In**: 300ms ease-out (component appearance)
- **Slide In**: 400ms ease-out (side panel entry)
- **Breathing**: 2s infinite (idle orb pulse)
- **Pulse Glow**: 2s infinite (action feedback)
- **Shimmer**: 2s infinite (loading state)
- **Float**: 3s infinite (hover effects)

## Component Usage

### OrbStatus
\`\`\`tsx
import { OrbStatus } from '@/components/orb-status';

export function Example() {
  return <OrbStatus state="listening" />;
}
\`\`\`

### RecorderButton
\`\`\`tsx
import { RecorderButton } from '@/components/recorder-button';

export function Example() {
  const handleAudio = (blob: Blob) => {
    // Send audio to backend
  };
  
  return (
    <RecorderButton 
      onAudioSubmit={handleAudio}
      isProcessing={false}
    />
  );
}
\`\`\`

### WebSocket Hook
\`\`\`tsx
import { useWebSocket } from '@/lib/hooks/use-ws';

export function Example() {
  const { isReady, sendAudio, error } = useWebSocket();
  
  return (
    <button onClick={() => sendAudio(audioBlob)}>
      Send Audio
    </button>
  );
}
\`\`\`

## Backend Integration

The frontend communicates with the Agora backend via:

### WebSocket Messages (Client → Server)
\`\`\`json
{
  "type": "audio",
  "session_id": "uuid",
  "user_id": "uuid",
  "format": "audio/webm",
  "data": "base64-encoded-audio"
}
\`\`\`

### WebSocket Messages (Server → Client)
\`\`\`json
{
  "type": "transcript",
  "from": "student|tutor",
  "text": "..."
}
\`\`\`

\`\`\`json
{
  "type": "visual",
  "action": "CREATE_NOTE|LOAD_IMAGE|HIGHLIGHT_REGION",
  "payload": { }
}
\`\`\`

### HTTP Endpoints
- `POST /api/materials/upload` - Upload course materials
- `GET /api/materials/status/{job_id}` - Check upload progress

## Performance Optimizations

- **Canvas Rendering**: Efficient whiteboard rendering with debouncing
- **Message Virtualization**: Scrollable transcript with smooth performance
- **Audio Compression**: WebM codec for optimal file size
- **Connection Pooling**: Automatic WebSocket reconnection
- **Lazy Loading**: Components load on demand

## Accessibility

- Keyboard navigation support (Tab, Enter, Space)
- ARIA labels for screen readers
- Focus indicators on all interactive elements
- High contrast colors (WCAG AA compliant)
- Voice control friendly design

## Troubleshooting

### WebSocket Connection Failed
- Verify backend is running on `http://localhost:8000`
- Check CORS headers in backend configuration
- Inspect browser console for detailed error messages

### Microphone Access Denied
- Grant microphone permission in browser settings
- Check browser privacy controls
- Try a different browser if issue persists

### Audio Not Playing
- Verify audio data is properly base64 encoded
- Check browser audio permissions
- Ensure audio context is not blocked by browser policies

### Materials Upload Fails
- Verify file size < 50MB
- Check supported file types (PDF, TXT, PNG, JPG, DOCX)
- Ensure backend `/api/materials/upload` endpoint is accessible

## Development Workflow

1. **Component Development**: Build in isolation, test with Storybook (optional)
2. **State Management**: Use Zustand stores for global state
3. **WebSocket Testing**: Use `wscat` to test backend messages
4. **Performance**: Monitor with React DevTools Profiler
5. **Accessibility**: Test with keyboard navigation and screen readers

## Build for Production

\`\`\`bash
npm run build
npm start
\`\`\`

Optimized build runs on `http://localhost:3000` with production settings.

## File Structure

\`\`\`
frontend/
├── app/
│   ├── layout.tsx           # Root layout with metadata
│   ├── page.tsx             # Main tutoring interface
│   └── globals.css          # Global styles and animations
├── components/
│   ├── orb-status.tsx       # Voice state orb
│   ├── recorder-button.tsx  # Push-to-talk button
│   ├── transcript-panel.tsx # Chat display
│   ├── whiteboard-pane.tsx  # Canvas whiteboard
│   ├── session-sidebar.tsx  # Session panel
│   ├── upload-panel.tsx     # File upload interface
│   └── loading-skeleton.tsx # Loading placeholders
├── lib/
│   ├── hooks/
│   │   └── use-ws.ts        # WebSocket hook
│   ├── services/
│   │   └── ws-client.ts     # WebSocket client
│   ├── store/
│   │   ├── messages.ts      # Messages store
│   │   └── session.ts       # Session store
│   ├── types/
│   │   └── messages.ts      # Message types
│   ├── utils/
│   │   ├── audio.ts         # Audio utilities
│   │   └── formatting.ts    # Text formatting
│   └── constants/
│       └── agora.ts         # Configuration
├── tailwind.config.ts       # Tailwind configuration
├── tsconfig.json            # TypeScript config
├── package.json             # Dependencies
└── .env.local               # Environment variables
\`\`\`

## Technologies

- **Framework**: Next.js 16 with React 19
- **Styling**: Tailwind CSS v4
- **State Management**: Zustand
- **WebSocket**: Socket.io-client
- **Type Safety**: TypeScript
- **UI Components**: Shadcn/ui

## Contributing

Follow these guidelines when contributing:
1. Use Nike-inspired design principles
2. Maintain smooth 300ms animations
3. Add TypeScript types for all props
4. Keep components focused and composable
5. Test WebSocket integration thoroughly

## License

MIT - Built for NYU Hackathon 2025
