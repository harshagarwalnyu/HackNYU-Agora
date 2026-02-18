'use client';

import { useRef } from 'react';

interface FileUploadInputProps {
  isDragging: boolean;
  isUploading: boolean;
  onDragOver: (e: React.DragEvent) => void;
  onDragLeave: (e: React.DragEvent) => void;
  onDrop: (e: React.DragEvent) => void;
  onFileSelect: (e: React.ChangeEvent<HTMLInputElement>) => void;
}

export function FileUploadInput({
  isDragging,
  isUploading,
  onDragOver,
  onDragLeave,
  onDrop,
  onFileSelect,
}: FileUploadInputProps) {
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleClick = () => {
    if (!isUploading) {
      fileInputRef.current?.click();
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (isUploading) return;
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      fileInputRef.current?.click();
    }
  };

  return (
    <div
      role="button"
      tabIndex={0}
      aria-label="Upload file drop zone"
      onKeyDown={handleKeyDown}
      onDragOver={onDragOver}
      onDragLeave={onDragLeave}
      onDrop={onDrop}
      onClick={handleClick}
      className={`flex-shrink-0 mx-4 mt-4 rounded-lg border-2 border-dashed transition-all
        flex flex-col items-center justify-center p-8
        focus-visible:ring-2 focus-visible:ring-white focus-visible:outline-none
        ${
          isDragging
            ? 'border-zinc-500 bg-zinc-900'
            : 'border-zinc-700 hover:border-zinc-600 hover:bg-zinc-900'
        }
        ${isUploading ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}
      `}
    >
      <input
        ref={fileInputRef}
        type="file"
        onChange={onFileSelect}
        disabled={isUploading}
        className="hidden"
        accept=".pdf,.txt,.png,.jpg,.jpeg,.docx,.pptx"
      />

      <div className="text-center">
        <svg
          className="w-10 h-10 mx-auto mb-2 text-zinc-500"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={1.5}
            d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"
          />
        </svg>
        <p className="text-sm font-medium text-white">
          {isUploading ? 'Uploading...' : 'Drop files or click to upload'}
        </p>
        <p className="text-xs text-zinc-500 mt-1">
          PDF, DOCX, PPTX, TXT, Images • Max 50MB
        </p>
      </div>
    </div>
  );
}
