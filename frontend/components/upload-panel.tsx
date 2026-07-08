'use client';

import { useCallback, useEffect, useState } from "react";
import { useSessionStore } from '@/lib/store/session';
import { useMaterialsStore } from '@/lib/store/materials';
import { listMaterials, uploadMaterial, pollJobStatus, validateFile } from '@/lib/services/materials-api';
import { FileUploadInput } from './file-upload-input';
import { UploadProgress } from './upload-progress';
import { MaterialItem } from './material-item';

interface UploadPanelProps {
  onUploadStart?: () => void;
  onUploadComplete?: (file: { name: string; type: string }) => void;
}

export function UploadPanel({
  onUploadStart,
  onUploadComplete,
}: UploadPanelProps) {
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

  const loadMaterials = useCallback(async () => {
    try {
      const mats = await listMaterials(userId, currentTopic);
      setMaterials(mats);
    } catch {
      // Silent fail - UI remains responsive
    }
  }, [userId, currentTopic, setMaterials]);

  useEffect(() => {
    loadMaterials();
  }, [loadMaterials]);

  async function handleFileInputChange(file: File) {
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
      addUploadingFile(uploadId, file.name);

      // Upload with progress tracking
      const response = await uploadMaterial(
        file,
        userId,
        currentTopic,
        (progress) => {
          updateUploadProgress(uploadId, progress);
        }
      );

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

      // Poll for completion using async/await pattern
      try {
        const finalStatus = await pollJobStatus(
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
        );

        onUploadComplete?.({ name: file.name, type: file.type });
      } catch (pollErr) {
        updateMaterial(response.job_id, {
          status: 'failed',
          message: pollErr instanceof Error ? pollErr.message : 'Processing failed',
        });
      }
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Upload failed';
      setError(message);
      removeUploadingFile(uploadId);
    }
  }

  function handleDragOver(e: React.DragEvent) {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(true);
  }

  function handleDragLeave(e: React.DragEvent) {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
  }

  function handleDrop(e: React.DragEvent) {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);

    const files = e.dataTransfer.files;
    if (files.length > 0) {
      handleFileInputChange(files[0]);
    }
  }

  function handleFileSelect(e: React.ChangeEvent<HTMLInputElement>) {
    const files = e.currentTarget.files;
    if (files && files.length > 0) {
      handleFileInputChange(files[0]);
    }
  }

  const isUploading = uploadingFiles.size > 0;

  return (
    <div className="flex flex-col h-full bg-black">
      {/* Header */}
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
                d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
              />
            </svg>
          </button>
        </div>
      </div>

      {/* Upload Input */}
      <FileUploadInput
        isDragging={isDragging}
        isUploading={isUploading}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        onFileSelect={handleFileSelect}
      />

      {/* Progress & Error */}
      <UploadProgress uploadingFiles={uploadingFiles} error={error} />

      {/* Materials List */}
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
