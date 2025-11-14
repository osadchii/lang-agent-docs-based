export interface ApiUser {
    id: string;
    telegram_id: number;
    first_name: string;
    last_name?: string | null;
    username?: string | null;
    is_premium: boolean;
    trial_ends_at?: string | null;
    created_at: string;
}

export interface ValidateInitDataResponse {
    user: ApiUser;
    token: string;
    expires_at: string;
}

export type ChatRole = 'user' | 'assistant' | 'system';

export interface ChatMessage {
    id: string;
    profile_id: string;
    role: ChatRole;
    content: string;
    timestamp: string;
}

export interface PaginationMeta {
    limit: number;
    offset: number;
    count: number;
    has_more: boolean;
    next_offset: number | null;
}

export interface ChatHistoryResponse {
    messages: ChatMessage[];
    pagination: PaginationMeta;
}

export interface ChatResponse {
    profile_id: string;
    message: ChatMessage;
}

export interface ChatRequestPayload {
    message: string;
    profile_id?: string;
}
