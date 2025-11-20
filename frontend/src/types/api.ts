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

export type StatsPeriod = 'week' | 'month' | '3months' | 'year' | 'all';

export type ActivityLevel = 'none' | 'low' | 'medium' | 'high';

export interface ActivityEntry {
    date: string;
    cards_studied: number;
    exercises_completed: number;
    time_minutes: number;
    activity_level?: ActivityLevel;
}

export interface StatsResponse {
    profile_id: string;
    language: string;
    current_level: string;
    period: StatsPeriod;
    streak: {
        current: number;
        best: number;
        total_days: number;
    };
    cards: {
        total: number;
        studied: number;
        new: number;
        stats: {
            know: number;
            repeat: number;
            dont_know: number;
        };
    };
    exercises: {
        total: number;
        stats: {
            correct: number;
            partial: number;
            incorrect: number;
        };
        accuracy: number;
    };
    time: {
        total_minutes: number;
        average_per_day: number;
    };
    activity: ActivityEntry[];
}

export interface StreakResponse {
    profile_id: string;
    current_streak: number;
    best_streak: number;
    total_active_days: number;
    today_completed: boolean;
    last_activity: string | null;
    streak_safe_until: string | null;
}

export interface CalendarResponse {
    data: ActivityEntry[];
}

export interface Deck {
    id: string;
    profile_id: string;
    name: string;
    description?: string | null;
    is_active: boolean;
    is_group: boolean;
    owner_id?: string | null;
    owner_name?: string | null;
    cards_count: number;
    new_cards_count: number;
    due_cards_count: number;
    created_at: string;
    updated_at: string;
}

export interface DeckListResponse {
    data: Deck[];
}

export type CardStatus = 'new' | 'learning' | 'review';
export type CardRating = 'know' | 'repeat' | 'dont_know';

export interface Card {
    id: string;
    deck_id: string;
    word: string;
    translation: string;
    example: string;
    example_translation: string;
    lemma: string;
    notes?: string | null;
    status: CardStatus;
    interval_days: number;
    next_review: string;
    reviews_count: number;
    ease_factor: number;
    last_rating?: CardRating | null;
    last_reviewed_at?: string | null;
    created_at: string;
    updated_at: string;
}

export interface CardListResponse {
    data: Card[];
    pagination: PaginationMeta;
}

export interface CardCreateResponse {
    created: Card[];
    duplicates: string[];
    failed: string[];
}

export interface NextCardResponse {
    id: string;
    deck_id: string;
    word: string;
    translation: string;
    example: string;
    example_translation: string;
    status: CardStatus;
    next_review: string;
}

export interface RateCardResponse {
    id: string;
    status: CardStatus;
    interval_days: number;
    next_review: string;
    reviews_count: number;
    last_rating: CardRating;
    last_reviewed_at: string;
}
