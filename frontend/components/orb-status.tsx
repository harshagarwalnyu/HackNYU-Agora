'use client';

import { useEffect, useRef } from 'react';

type OrbState = 'idle' | 'listening' | 'thinking' | 'speaking';

interface OrbStatusProps {
  state: OrbState;
}

export function OrbStatus({ state }: OrbStatusProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    let animationId: number;
    let time = 0;

    const animate = () => {
      time += 0.016;
      const width = canvas.width;
      const height = canvas.height;
      const centerX = width / 2;
      const centerY = height / 2;

      ctx.clearRect(0, 0, width, height);

      const stateConfig = {
        idle: { baseRadius: 35, color: '#111111', pulseScale: 1 + Math.sin(time * 2) * 0.08 },
        listening: { baseRadius: 40, color: '#0066FF', pulseScale: 1 + Math.sin(time * 3) * 0.15 },
        thinking: { baseRadius: 38, color: '#FF6B00', pulseScale: 1 + Math.sin(time * 2.5) * 0.1 },
        speaking: { baseRadius: 42, color: '#FF6B00', pulseScale: 1 + Math.cos(time * 4) * 0.12 },
      };

      const config = stateConfig[state];
      const radius = config.baseRadius * config.pulseScale;

      const gradient = ctx.createRadialGradient(centerX, centerY, 0, centerX, centerY, radius * 1.8);
      gradient.addColorStop(0, `${config.color}40`);
      gradient.addColorStop(0.7, `${config.color}10`);
      gradient.addColorStop(1, `${config.color}00`);

      ctx.fillStyle = gradient;
      ctx.fillRect(0, 0, width, height);

      ctx.fillStyle = config.color;
      ctx.beginPath();
      ctx.arc(centerX, centerY, radius, 0, Math.PI * 2);
      ctx.fill();

      if (state === 'thinking') {
        ctx.fillStyle = `${config.color}60`;
        for (let i = 0; i < 3; i++) {
          const angle = (time * 1.5 + (i * Math.PI * 2) / 3);
          const x = centerX + Math.cos(angle) * (radius + 30);
          const y = centerY + Math.sin(angle) * (radius + 30);
          const particleSize = 8 + Math.sin(time * 4 + i) * 3;
          ctx.beginPath();
          ctx.arc(x, y, particleSize, 0, Math.PI * 2);
          ctx.fill();
        }
      }

      animationId = requestAnimationFrame(animate);
    };

    animate();

    return () => cancelAnimationFrame(animationId);
  }, [state]);

  const stateLabels = {
    idle: 'Ready to listen',
    listening: 'Listening...',
    thinking: 'Thinking...',
    speaking: 'Tutor speaking',
  };

  return (
    <div className="flex flex-col items-center gap-4">
      <div className="relative w-32 h-32">
        <canvas
          ref={canvasRef}
          width={128}
          height={128}
          className="w-full h-full"
        />
      </div>
      <p className="text-sm text-primary-light font-medium tracking-wide">
        {stateLabels[state]}
      </p>
    </div>
  );
}
