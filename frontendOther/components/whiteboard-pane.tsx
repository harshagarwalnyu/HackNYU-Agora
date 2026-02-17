'use client';

import { useEffect, useRef, useState, useImperativeHandle, forwardRef } from 'react';

interface WhiteboardPaneProps {
  onDrawingChange?: (data: any) => void;
  isReadOnly?: boolean;
}

export interface WhiteboardPaneRef {
  addNote: (text: string, x?: number, y?: number) => void;
  addImage: (imageSrc: string, x?: number, y?: number) => void;
  clear: () => void;
  export: () => void;
}

export const WhiteboardPane = forwardRef<WhiteboardPaneRef, WhiteboardPaneProps>(
  ({ onDrawingChange, isReadOnly = false }, ref) => {
    const canvasRef = useRef<HTMLCanvasElement>(null);
    const containerRef = useRef<HTMLDivElement>(null);
    const [isDrawing, setIsDrawing] = useState(false);
    const [context, setContext] = useState<CanvasRenderingContext2D | null>(null);
    const [notes, setNotes] = useState<Array<{ id: string; text: string; x: number; y: number }>>([]);

    const drawNote = (ctx: CanvasRenderingContext2D | null, note: any) => {
      if (!ctx) return;

      const width = 200;
      const height = 150;

      // Note background (dark gray for blackboard)
      ctx.fillStyle = '#27272a';  // zinc-800
      ctx.fillRect(note.x, note.y, width, height);

      // Note border
      ctx.strokeStyle = '#52525b';  // zinc-600
      ctx.lineWidth = 2;
      ctx.strokeRect(note.x, note.y, width, height);

      // Text (light for visibility)
      ctx.fillStyle = '#e4e4e7';  // zinc-200
      ctx.font = '14px Inter, system-ui';
      ctx.textBaseline = 'top';

      // Word wrap text
      const words = note.text.split(' ');
      let line = '';
      let y = note.y + 15;
      const lineHeight = 20;
      const maxWidth = width - 20;

      words.forEach((word: string) => {
        const testLine = line + word + ' ';
        const metrics = ctx.measureText(testLine);
        if (metrics.width > maxWidth && line) {
          ctx.fillText(line, note.x + 10, y);
          line = word + ' ';
          y += lineHeight;
        } else {
          line = testLine;
        }
      });
      ctx.fillText(line, note.x + 10, y);
    };

    const addNote = (text: string, x: number = Math.random() * 300, y: number = Math.random() * 300) => {
      const note = {
        id: `note-${Date.now()}`,
        text,
        x,
        y,
      };
      setNotes((prev) => [...prev, note]);
      if (context) {
        drawNote(context, note);
      }
    };

    const addImage = (imageSrc: string, x: number = 50, y: number = 50) => {
      if (!context) return;
      const img = new Image();
      img.crossOrigin = 'anonymous';
      img.src = imageSrc;
      img.onload = () => {
        const width = 300;
        const height = (img.height / img.width) * width;
        context.drawImage(img, x, y, width, height);
      };
    };

    const handleMouseDown = (e: React.MouseEvent) => {
      if (isReadOnly) return;
      setIsDrawing(true);
      const canvas = canvasRef.current;
      if (!canvas || !context) return;
      const rect = canvas.getBoundingClientRect();
      context.beginPath();
      context.moveTo(e.clientX - rect.left, e.clientY - rect.top);
    };

    const handleMouseMove = (e: React.MouseEvent) => {
      if (!isDrawing || !context) return;
      const canvas = canvasRef.current;
      if (!canvas) return;
      const rect = canvas.getBoundingClientRect();
      context.lineTo(e.clientX - rect.left, e.clientY - rect.top);
      context.strokeStyle = '#e4e4e7';  // zinc-200 - chalk white
      context.lineWidth = 3;
      context.lineCap = 'round';
      context.lineJoin = 'round';
      context.stroke();
    };

    const handleMouseUp = () => {
      setIsDrawing(false);
      if (context) {
        context.closePath();
      }
    };

    const handleClear = () => {
      const canvas = canvasRef.current;
      if (!canvas || !context) return;
      context.fillStyle = '#09090b';  // zinc-950 - blackboard
      context.fillRect(0, 0, canvas.width, canvas.height);
      setNotes([]);
    };

    const handleExport = () => {
      const canvas = canvasRef.current;
      if (!canvas) return;
      const link = document.createElement('a');
      link.href = canvas.toDataURL('image/png');
      link.download = `whiteboard-${Date.now()}.png`;
      link.click();
    };

    // Expose methods via ref
    useImperativeHandle(ref, () => ({
      addNote,
      addImage,
      clear: handleClear,
      export: handleExport,
    }));

    useEffect(() => {
      const canvas = canvasRef.current;
      if (!canvas) return;

      const updateCanvasSize = () => {
        const rect = canvas.getBoundingClientRect();
        canvas.width = rect.width;
        canvas.height = rect.height;

        const ctx = canvas.getContext('2d');
        if (ctx) {
          ctx.fillStyle = '#09090b';  // zinc-950 - blackboard
          ctx.fillRect(0, 0, canvas.width, canvas.height);

          // Redraw existing notes
          notes.forEach(note => drawNote(ctx, note));

          setContext(ctx);
        }
      };

      updateCanvasSize();

      // Handle window resize
      window.addEventListener('resize', updateCanvasSize);
      return () => window.removeEventListener('resize', updateCanvasSize);
    }, [notes]);

    return (
      <div ref={containerRef} className="flex flex-col h-full w-full bg-zinc-900 overflow-hidden">
        <div className="flex items-center justify-between p-4 border-b border-zinc-800 flex-shrink-0">
          <h2 className="text-2xl font-bold text-white">Blackboard</h2>
          <div className="flex gap-3">
            {!isReadOnly && (
              <>
                <button
                  onClick={handleClear}
                  className="px-4 py-2 text-sm font-medium text-white bg-zinc-800 rounded-lg hover:bg-zinc-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                  type="button"
                >
                  Clear
                </button>
                <button
                  onClick={handleExport}
                  className="px-4 py-2 text-sm font-medium text-white bg-zinc-700 rounded-lg hover:bg-zinc-600 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                  type="button"
                >
                  Export
                </button>
              </>
            )}
          </div>
        </div>

        <div className="flex-1 overflow-hidden relative">
          <canvas
            ref={canvasRef}
            onMouseDown={handleMouseDown}
            onMouseMove={handleMouseMove}
            onMouseUp={handleMouseUp}
            onMouseLeave={handleMouseUp}
            className={`w-full h-full ${!isReadOnly && 'cursor-crosshair'}`}
            style={{ display: 'block', backgroundColor: '#09090b' }}
          />
        </div>
      </div>
    );
  }
);

WhiteboardPane.displayName = 'WhiteboardPane';
