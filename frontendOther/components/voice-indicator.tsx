'use client';

import { useEffect, useRef } from 'react';

interface VoiceIndicatorProps {
  audioContext?: AudioContext;
  stream?: MediaStream;
}

export function VoiceIndicator({ audioContext, stream }: VoiceIndicatorProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const analyserRef = useRef<AnalyserNode | null>(null);

  useEffect(() => {
    if (!audioContext || !stream) return;

    try {
      const analyser = audioContext.createAnalyser();
      analyser.fftSize = 256;
      const source = audioContext.createMediaStreamSource(stream);
      source.connect(analyser);

      analyserRef.current = analyser;

      const canvas = canvasRef.current;
      if (!canvas) return;

      const ctx = canvas.getContext('2d');
      if (!ctx) return;

      const bufferLength = analyser.frequencyBinCount;
      const dataArray = new Uint8Array(bufferLength);

      const draw = () => {
        analyser.getByteFrequencyData(dataArray);

        ctx.fillStyle = '#F5F5F5';
        ctx.fillRect(0, 0, canvas.width, canvas.height);

        const barWidth = (canvas.width / bufferLength) * 2.5;
        let x = 0;

        for (let i = 0; i < bufferLength; i++) {
          const barHeight = (dataArray[i] / 255) * canvas.height;

          ctx.fillStyle = `hsl(${i / bufferLength * 360}, 100%, 50%)`;
          ctx.fillRect(x, canvas.height - barHeight, barWidth, barHeight);

          x += barWidth + 1;
        }

        requestAnimationFrame(draw);
      };

      draw();
    } catch (error) {
      console.error('[Agora] Audio context setup failed:', error);
    }
  }, [audioContext, stream]);

  return (
    <canvas
      ref={canvasRef}
      width={200}
      height={60}
      className="w-full h-auto bg-secondary-dark rounded"
    />
  );
}
