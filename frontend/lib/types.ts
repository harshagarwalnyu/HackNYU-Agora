export type UserRole = 'student' | 'tutor';

export interface TranscriptMessage {
    from: UserRole;
    text: string;
}

export interface AudioResponseMessage {
    data: string;
    format: string;
    session_id: string;
}

export interface Message {
    id: string;
    from: UserRole;
    text: string;
    timestamp: Date;
}

export interface VisualAction {
    action: 'CREATE_NOTE' | 'LOAD_IMAGE' | 'CLEAR_BOARD';
    payload: {
        text?: string;
        imageSrc?: string;
        x?: number;
        y?: number;
    };
}

export interface SessionStatus {
    status: 'active' | 'complete' | 'interrupted' | 'cancelled';
    session_id: string;
}

export interface ConnectionStatus {
    connected: boolean;
}

export interface ErrorMessage {
    message: string;
}

export interface SessionInitialized {
    session_id: string;
    user_id: string;
}

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
