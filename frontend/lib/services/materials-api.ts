import { API_CONFIG } from '../constants';
import { Material, JobStatus, UploadResponse } from '../types';
import { validateFile, formatFileSize, getFileIcon } from '../utils/files';

const API_BASE = API_CONFIG.BASE_URL;

export type { Material, JobStatus, UploadResponse };

/**
 * Upload a document or image for processing
 */
export async function uploadMaterial(
    file: File,
    userId: string,
    courseId?: string,
    onProgress?: (progress: number) => void
): Promise<UploadResponse> {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('user_id', userId);
    if (courseId) formData.append('course_id', courseId);

    if (onProgress) onProgress(50); // Simple progress indicator

    const response = await fetch(`${API_BASE}/api/materials/upload`, {
        method: 'POST',
        body: formData,
    });

    if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Upload failed');
    }

    if (onProgress) onProgress(100);
    return response.json();
}

/**
 * List all materials for a user/course
 */
export async function listMaterials(userId: string, courseId?: string): Promise<Material[]> {
    const url = new URL(`${API_BASE}/api/materials/list`);
    url.searchParams.append('user_id', userId);
    if (courseId) url.searchParams.append('course_id', courseId);

    const response = await fetch(url.toString());
    if (!response.ok) throw new Error('Failed to list materials');

    const data = await response.json();
    return data.materials || [];
}

/**
 * Poll for job completion
 */
export async function pollJobStatus(
    jobId: string,
    onStatus: (status: JobStatus) => void,
    interval = API_CONFIG.TIMEOUTS.POLLING_INTERVAL,
    maxAttempts = 30
): Promise<JobStatus> {
    let attempts = 0;

    return new Promise((resolve, reject) => {
        const poll = async () => {
            try {
                const response = await fetch(`${API_BASE}/api/materials/status/${jobId}`);
                if (!response.ok) throw new Error('Failed to fetch status');

                const status: JobStatus = await response.json();
                onStatus(status);

                if (status.status === 'completed' || status.status === 'failed') {
                    resolve(status);
                    return;
                }

                attempts++;
                if (attempts >= maxAttempts) {
                    reject(new Error('Polling timed out'));
                    return;
                }

                setTimeout(poll, interval);
            } catch (err) {
                reject(err);
            }
        };

        poll();
    });
}

export { validateFile, formatFileSize, getFileIcon };
