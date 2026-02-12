'use client';

import { useEffect, useRef, useState } from 'react';
import { useSessionStore } from '@/lib/store/session';
import { useMaterialsStore } from '@/lib/store/materials';
import {
  uploadMaterial,
  pollJobStatus,
  listMaterials,
  validateFile,
  formatFileSize,
  getFileIcon,
} from '@/lib/services/materials-api';

interface UploadPanelProps {
  onUploadStart?: () => void;
  onUploadComplete?: (file: { name: string; type: string }) => void;
}

export function UploadPanel({
  onUploadStart,
  onUploadComplete,
}: UploadPanelProps) {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const { userId, currentTopic } = useSessionStore();
  const {
    materials,
    uploadingFiles,
    addMaterial,
    updateMaterial,
    removeMaterial,
    addUploadingFile,
    updateUploadProgress,
    removeUploadingFile,
    setMaterials,
  } = useMaterialsStore();

  // Load materials on mount
  useEffect(() => {
    loadMaterials();
  }, [userId, currentTopic]);

  const loadMaterials = async () => {
    try {
      const mats = await listMaterials(userId, currentTopic);
      setMaterials(mats);
    } catch (err) {
      console.error('[Materials] Failed to load:', err);
    }
  };

  const uploadFile = async (file: File) => {
    if (!file) return;

    // Validate file
    const validation = validateFile(file);
    if (!validation.valid) {
      setError(validation.error || 'Invalid file');
      return;
    }

    const uploadId = `upload-${Date.now()}`;
    setError(null);
    onUploadStart?.();

    try {
      // Add to uploading files
      addUploadingFile(uploadId, file.name);

      // Upload with progress tracking
      const response = await uploadMaterial(
        file,
        userId,
        currentTopic,
        undefined,
        (progress) => {
          updateUploadProgress(uploadId, progress);
        }
      );

      console.log('[Materials] Upload started:', response.job_id);

      // Remove from uploading files
      removeUploadingFile(uploadId);

      // Add to materials with processing status
      addMaterial({
        job_id: response.job_id,
        filename: file.name,
        status: 'processing',
        progress: 0,
        message: response.message,
        user_id: userId,
        course_id: currentTopic,
      });

      // Poll for completion
      pollJobStatus(
        response.job_id,
        (status) => {
          updateMaterial(response.job_id, {
            status: status.status,
            progress: status.progress,
            message: status.message,
          });
        },
        1000,
        60
      )
        .then((finalStatus) => {
          console.log('[Materials] Processing complete:', finalStatus.job_id);
          onUploadComplete?.({ name: file.name, type: file.type });
        })
        .catch((err) => {
          console.error('[Materials] Processing failed:', err);
          updateMaterial(response.job_id, {
            status: 'failed',
            message: err.message || 'Processing failed',
          });
        });
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Upload failed';
      setError(message);
      removeUploadingFile(uploadId);
      console.error('[Materials] Upload error:', err);
    }
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);

    const files = e.dataTransfer.files;
    if (files.length > 0) {
      uploadFile(files[0]);
    }
  };

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.currentTarget.files;
    if (files && files.length > 0) {
      uploadFile(files[0]);
    }
  };

  const isUploading = uploadingFiles.size > 0;

  return (
    <div className="flex flex-col h-full bg-black">
      <div className="flex-shrink-0 px-4 py-3 border-b border-zinc-800">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-sm font-bold text-white">Materials</h3>
            <p className="text-xs text-zinc-500 mt-0.5">
              {materials.length} file{materials.length !== 1 ? 's' : ''} uploaded
            </p>
          </div>
          <button
            onClick={loadMaterials}
            className="p-1.5 rounded hover:bg-zinc-800 text-zinc-400 hover:text-white transition-colors"
            title="Refresh"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
            </svg>
          </button>
        </div>
      </div>

      <div
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        onClick={() => !isUploading && fileInputRef.current?.click()}
        className={`flex-shrink-0 mx-4 mt-4 rounded-lg border-2 border-dashed transition-all cursor-pointer
          flex flex-col items-center justify-center p-8
          ${
            isDragging
              ? 'border-zinc-500 bg-zinc-900'
              : 'border-zinc-700 hover:border-zinc-600 hover:bg-zinc-900'
          }
          ${isUploading ? 'opacity-50 cursor-not-allowed' : ''}
        `}
      >
        <input
          ref={fileInputRef}
          type="file"
          onChange={handleFileSelect}
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

      {/* Uploading files */}
      {uploadingFiles.size > 0 && (
        <div className="flex-shrink-0 px-4 pt-4">
          {Array.from(uploadingFiles.entries()).map(([id, file]) => (
            <div key={id} className="mb-3">
              <div className="flex items-center justify-between mb-1">
                <span className="text-xs text-zinc-400 truncate">{file.filename}</span>
                <span className="text-xs text-zinc-500">{Math.round(file.progress)}%</span>
              </div>
              <div className="h-1 bg-zinc-800 rounded-full overflow-hidden">
                <div
                  className="h-full bg-blue-500 transition-all duration-300"
                  style={{ width: `${file.progress}%` }}
                />
              </div>
            </div>
          ))}
        </div>
      )}

      {error && (
        <div className="mx-4 mt-3 p-3 bg-red-500/10 border border-red-500/30 rounded-lg">
          <p className="text-xs text-red-400">{error}</p>
        </div>
      )}

      {/* Materials list */}
      <div className="flex-1 overflow-y-auto px-4 pb-4">
        <div className="mt-4">
          <p className="text-xs font-semibold text-zinc-400 uppercase tracking-wide mb-3">
            Your Materials
          </p>
          {materials.length === 0 ? (
            <p className="text-xs text-zinc-500 italic text-center py-8">
              No materials uploaded yet
            </p>
          ) : (
            <div className="space-y-2">
              {materials.map((material) => (
                <MaterialItem
                  key={material.job_id}
                  material={material}
                  onRemove={() => removeMaterial(material.job_id)}
                />
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function MaterialItem({
  material,
  onRemove,
}: {
  material: any;
  onRemove: () => void;
}) {
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
              {material.status === 'processing' && (
                <span className="text-xs text-zinc-500">{material.progress}%</span>
              )}
            </div>
            {material.message && material.status !== 'completed' && (
              <p className="text-xs text-zinc-500 mt-1 truncate">{material.message}</p>
            )}
          </div>
        </div>
        <button
          onClick={onRemove}
          className="p-1 text-zinc-500 hover:text-red-400 transition-colors"
          title="Remove"
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>
      {material.status === 'processing' && material.progress > 0 && (
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
