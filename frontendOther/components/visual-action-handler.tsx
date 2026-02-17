'use client';

import { useRef } from 'react';

export type VisualAction = 
  | { type: 'CREATE_NOTE'; payload: { text: string; x?: number; y?: number } }
  | { type: 'LOAD_IMAGE'; payload: { imageSrc: string; x?: number; y?: number } }
  | { type: 'HIGHLIGHT_REGION'; payload: { x: number; y: number; width: number; height: number; color?: string } }
  | { type: 'CLEAR_BOARD'; payload: {} };

interface VisualActionHandlerProps {
  whiteboardRef: React.RefObject<any>;
  onAction?: (action: VisualAction) => void;
}

export function VisualActionHandler({ whiteboardRef, onAction }: VisualActionHandlerProps) {
  const handleVisualAction = (action: VisualAction) => {
    const whiteboard = whiteboardRef.current;
    if (!whiteboard) return;

    switch (action.type) {
      case 'CREATE_NOTE':
        whiteboard.addNote?.(
          action.payload.text,
          action.payload.x,
          action.payload.y
        );
        break;
      case 'LOAD_IMAGE':
        whiteboard.addImage?.(
          action.payload.imageSrc,
          action.payload.x,
          action.payload.y
        );
        break;
      case 'CLEAR_BOARD':
        whiteboard.clear?.();
        break;
      case 'HIGHLIGHT_REGION':
        // Highlight implementation for future
        break;
    }

    onAction?.(action);
  };

  return {
    handleVisualAction,
  };
}
