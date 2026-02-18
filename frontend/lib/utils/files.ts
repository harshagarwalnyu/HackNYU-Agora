import { APP_CONFIG } from '../constants';

/**
 * Validate file type and size against app configuration
 */
export function validateFile(file: File) {
    const { MAX_SIZE, ALLOWED_TYPES } = APP_CONFIG.FILE_LIMITS;

    if (file.size > MAX_SIZE) {
        return { valid: false, error: `File size exceeds ${MAX_SIZE / (1024 * 1024)}MB limit` };
    }

    if (!(ALLOWED_TYPES as readonly string[]).includes(file.type)) {
        return { valid: false, error: 'Unsupported file type' };
    }

    return { valid: true };
}

/**
 * Helper to format file size into human-readable string
 */
export function formatFileSize(bytes: number): string {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

/**
 * Helper to get icon for file type based on extension
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
