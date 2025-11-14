import { httpClient } from './httpClient';
import type { ChatHistoryResponse, ChatRequestPayload, ChatResponse } from '../types/api';

interface HistoryParams {
    profileId?: string;
    limit?: number;
    offset?: number;
}

export async function sendChatMessage(payload: ChatRequestPayload): Promise<ChatResponse> {
    const { data } = await httpClient.post<ChatResponse>('/sessions/chat', {
        message: payload.message,
        profile_id: payload.profile_id,
    });
    return data;
}

export async function fetchChatHistory(params: HistoryParams): Promise<ChatHistoryResponse> {
    const query: Record<string, number | string> = {};
    if (params.profileId) {
        query.profile_id = params.profileId;
    }
    if (typeof params.limit === 'number') {
        query.limit = params.limit;
    }
    if (typeof params.offset === 'number') {
        query.offset = params.offset;
    }

    const { data } = await httpClient.get<ChatHistoryResponse>('/dialog/history', {
        params: query,
    });

    return data;
}
