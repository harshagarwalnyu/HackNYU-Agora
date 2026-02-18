'use client';

import { getFileIcon } from '@/lib/services/materials-api';
import type { Material } from '@/lib/types';

interface MaterialItemProps {
  material: Material;
  onRemove: () => void;
}

export function MaterialItem({ material, onRemove }: MaterialItemProps) {
  const getStatusColor = () => {
    switch (material.status) {
      case 'completed':
        return 'text-green-400';
      case 'failed':
        return 'text-red-400';
      case 'processing':
        return 'text-yellow-400';
      default:
        return 'text-zinc-400';
    }
  };

  const getStatusIcon = () => {
    switch (material.status) {
      case 'completed':
        return '✓';
      case 'failed':
        return '✗';
      case 'processing':
        return '⟳';
      default:
        return '•';
    }
  };

  const isProcessing = material.status === 'processing';
  const hasProgress = isProcessing && material.progress > 0;

  return (
    <div className="p-3 bg-zinc-900 border border-zinc-800 rounded-lg hover:border-zinc-700 transition-colors">
      <div className="flex items-start justify-between gap-2">
        <div className="flex items-start gap-2 flex-1 min-w-0">
          <span className="text-lg mt-0.5">{getFileIcon(material.filename)}</span>
          <div className="flex-1 min-w-0">
            <p className="text-xs text-white truncate font-medium">
              {material.filename}
            </p>
            <div className="flex items-center gap-2 mt-1">
              <span className={`text-xs font-medium ${getStatusColor()}`}>
                {getStatusIcon()} {material.status}
              </span>
              {isProcessing && (
                <span className="text-xs text-zinc-500">{material.progress}%</span>
              )}
            </div>
            {material.message && material.status !== 'completed' && (
              <p className="text-xs text-zinc-500 mt-1 truncate">
                {material.message}
              </p>
            )}
          </div>
        </div>
        <button
          onClick={onRemove}
          className="p-1 text-zinc-500 hover:text-red-400 transition-colors"
          title="Remove"
        >
          <svg
            className="w-4 h-4"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M6 18L18 6M6 6l12 12"
            />
          </svg>
        </button>
      </div>
      {hasProgress && (
        <div className="mt-2 h-1 bg-zinc-800 rounded-full overflow-hidden">
          <div
            className="h-full bg-yellow-500 transition-all duration-300"
            style={{ width: `${material.progress}%` }}
          />
        </div>
      )}
    </div>
  );
}
