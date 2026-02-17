export type WebSocketMessageType = 
  | 'audio'
  | 'text'
  | 'transcript'
  | 'audio_response'
  | 'visual'
  | 'session_start'
  | 'session_end';

export interface AudioMessage {
  type: 'audio';
  session_id: string;
  user_id: string;
  format: string;
  data: string; // base64
}

export interface TextMessage {
  type: 'text';
  session_id: string;
  user_id: string;
  text: string;
}

export interface TranscriptMessage {
  type: 'transcript';
  from: 'student' | 'tutor';
  text: string;
}

export interface AudioResponseMessage {
  type: 'audio_response';
  session_id: string;
  data: string; // base64 audio
  format: string;
}

export interface VisualMessage {
  type: 'visual';
  action: string;
  payload: any;
}

export type WebSocketMessage =
  | AudioMessage
  | TextMessage
  | TranscriptMessage
  | AudioResponseMessage
  | VisualMessage;
