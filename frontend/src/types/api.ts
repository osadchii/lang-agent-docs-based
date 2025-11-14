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

export type CEFRLevel = 'A1' | 'A2' | 'B1' | 'B2' | 'C1' | 'C2';

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

export interface LanguageProfileProgress {
    cards_count: number;
    exercises_count: number;
    streak: number;
}

export interface LanguageProfile {
    id: string;
    user_id: string;
    language: string;
    language_name: string;
    current_level: CEFRLevel;
    target_level: CEFRLevel;
    goals: string[];
    interface_language: string;
    is_active: boolean;
    progress: LanguageProfileProgress;
    created_at: string;
    updated_at: string;
}

export interface LanguageProfileListResponse {
    data: LanguageProfile[];
}

export interface LanguageProfileCreatePayload {
    language: string;
    current_level: CEFRLevel;
    target_level: CEFRLevel;
    goals: string[];
    interface_language: string;
}

export interface LanguageProfileUpdatePayload {
    current_level?: CEFRLevel;
    target_level?: CEFRLevel;
    goals?: string[];
    interface_language?: string;
}
