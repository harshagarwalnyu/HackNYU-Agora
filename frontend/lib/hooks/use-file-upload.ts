import { useCallback } from 'react';
import {
  uploadMaterial,
  pollJobStatus,
  validateFile,
} from '@/lib/services/materials-api';

export interface UploadCallbacks {
  onStart?: () => void;
  onProgress?: (progress: number) => void;
  onComplete?: (file: { name: string; type: string }) => void;
  onError?: (error: string) => void;
  onStatusChange?: (data: {
    status: string;
    progress: number;
    message: string;
  }) => void;
}

export function useFileUpload(
  userId: string,
  currentTopic: string,
  callbacks: UploadCallbacks = {}
) {
  const uploadFile = useCallback(
    async (file: File): Promise<void> => {
      if (!file) return;

      // Validate file
      const validation = validateFile(file);
      if (!validation.valid) {
        callbacks.onError?.(validation.error || 'Invalid file');
        return;
      }

      try {
        callbacks.onStart?.();

        // Upload with progress tracking
        const response = await uploadMaterial(
          file,
          userId,
          currentTopic,
          (progress) => {
            callbacks.onProgress?.(progress);
          }
        );

        // Poll for completion with async/await instead of promise chain
        const finalStatus = await pollJobStatus(
          response.job_id,
          (status) => {
            callbacks.onStatusChange?.({
              status: status.status,
              progress: status.progress,
              message: status.message ?? '',
            });
          },
          1000,
          60
        );

        callbacks.onComplete?.({ name: file.name, type: file.type });
      } catch (err) {
        const message =
          err instanceof Error ? err.message : 'Upload failed';
        callbacks.onError?.(message);
      }
    },
    [userId, currentTopic, callbacks]
  );

  return { uploadFile };
}
