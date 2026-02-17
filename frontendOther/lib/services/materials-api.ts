/**
 * Materials API Service
 * Handles file uploads, status polling, and material listing for the Agora frontend.
 */

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export interface Material {
    job_id: string;
    filename: string;
    status: 'processing' | 'completed' | 'failed';
    progress: number;
    message?: string;
    user_id: string;
    course_id?: string;
}

export interface JobStatus {
    job_id: string;
    status: 'processing' | 'completed' | 'failed';
    progress: number;
    message?: string;
}

export interface UploadResponse {
    job_id: string;
    status: string;
    message: string;
}

/**
 * 
 * Upload a document or image for processing
 */
export async function uploadMaterial(
    file: File,
    userId: string,
    courseId?: string,
    _ignored?: any,
    onProgress?: (progress: number) => void
): Promise<UploadResponse> {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('user_id', userId);
    if (courseId) formData.append('course_id', courseId);

    // Note: Standard fetch doesn't support upload progress. 
    // In a production app, we'd use XMLHttpRequest or a library like axios.
    // For now, we simulate progress or just call the API.
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
    // API returns { materials: [], count: n }
    return data.materials || [];
}

/**
 * Poll for job completion
 */
export async function pollJobStatus(
    jobId: string,
    onStatus: (status: JobStatus) => void,
    interval = 2000,
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

/**
 * Validate file type and size
 */
export function validateFile(file: File) {
    const MAX_SIZE = 50 * 1024 * 1024; // 50MB
    const ALLOWED_TYPES = [
        'application/pdf',
        'text/plain',
        'image/png',
        'image/jpeg',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        'application/vnd.openxmlformats-officedocument.presentationml.presentation',
    ];

    if (file.size > MAX_SIZE) {
        return { valid: false, error: 'File size exceeds 50MB limit' };
    }

    if (!ALLOWED_TYPES.includes(file.type)) {
        return { valid: false, error: 'Unsupported file type' };
    }

    return { valid: true };
}

/**
 * Helper to format file size
 */
export function formatFileSize(bytes: number): string {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

/**
 * Helper to get icon for file type
 */
export function getFileIcon(filename: string): string {
    const ext = filename.split('.').pop()?.toLowerCase();
    switch (ext) {
        case 'pdf': return '📄';
        case 'doc':
        case 'docx': return '📝';
        case 'ppt':
        case 'pptx': return '📊';
        case 'txt': return '🗒️';
        case 'png':
        case 'jpg':
        case 'jpeg': return '🖼️';
        default: return '📁';
    }
}
