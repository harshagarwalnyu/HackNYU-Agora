'use client';

import { useEffect, useRef, useState } from 'react';

interface RecorderButtonProps {
  onAudioSubmit: (blob: Blob) => void;
  disabled?: boolean;
  isProcessing?: boolean;
}

export function RecorderButton({
  onAudioSubmit,
  disabled = false,
  isProcessing = false,
}: RecorderButtonProps) {
  const [isRecording, setIsRecording] = useState(false);
  const [isPressed, setIsPressed] = useState(false);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const streamRef = useRef<MediaStream | null>(null);

  useEffect(() => {
    const initRecorder = async () => {
      try {
        const stream = await navigator.mediaDevices.getUserMedia({
          audio: { echoCancellation: true, noiseSuppression: true },
        });
        streamRef.current = stream;

        const mediaRecorder = new MediaRecorder(stream, {
          mimeType: 'audio/webm',
        });

        mediaRecorder.onstart = () => {
          chunksRef.current = [];
          setIsRecording(true);
        };

        mediaRecorder.ondataavailable = (e) => {
          if (e.data.size > 0) {
            chunksRef.current.push(e.data);
          }
        };

        mediaRecorder.onstop = () => {
          const blob = new Blob(chunksRef.current, { type: 'audio/webm' });
          setIsRecording(false);
          onAudioSubmit(blob);
        };

        mediaRecorderRef.current = mediaRecorder;
      } catch (error) {
        console.error('[Agora] Microphone access denied:', error);
      }
    };

    initRecorder();

    return () => {
      if (streamRef.current) {
        streamRef.current.getTracks().forEach((track) => track.stop());
      }
    };
  }, [onAudioSubmit]);

  const handlePointerDown = () => {
    if (disabled || isProcessing) return;
    setIsPressed(true);
    mediaRecorderRef.current?.start();
  };

  const handlePointerUp = () => {
    setIsPressed(false);
    mediaRecorderRef.current?.stop();
  };

  const handlePointerLeave = () => {
    if (isPressed && mediaRecorderRef.current?.state === 'recording') {
      handlePointerUp();
    }
  };

  return (
    <button
      onPointerDown={handlePointerDown}
      onPointerUp={handlePointerUp}
      onPointerLeave={handlePointerLeave}
      disabled={disabled || isProcessing}
      className={`
        relative w-24 h-24 rounded-full font-semibold text-white
        transition-all duration-200 ease-out
        flex items-center justify-center text-sm
        ${
          isPressed
            ? 'scale-90 bg-accent shadow-lg'
            : isRecording
              ? 'scale-100 bg-accent animate-pulse-slow'
              : isProcessing
                ? 'scale-95 bg-primary-light cursor-wait'
                : 'scale-100 bg-primary hover:scale-105 active:scale-95'
        }
        disabled:opacity-50 disabled:cursor-not-allowed
        focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-accent
      `}
      aria-label={
        isRecording ? 'Recording... Release to send' : 'Hold to record'
      }
    >
      <div className="flex flex-col items-center gap-1">
        <svg
          className="w-6 h-6"
          fill="currentColor"
          viewBox="0 0 24 24"
        >
          <path d="M12 14c1.66 0 3-1.34 3-3V5c0-1.66-1.34-3-3-3S9 3.34 9 5v6c0 1.66 1.34 3 3 3z" />
        </svg>
        {isRecording && (
          <span className="text-xs font-bold tracking-widest">REC</span>
        )}
      </div>

      {isRecording && (
        <div className="absolute inset-0 rounded-full border-2 border-white opacity-50 animate-pulse" />
      )}
    </button>
  );
}
