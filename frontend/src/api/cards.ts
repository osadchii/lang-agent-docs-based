import type {
    CardCreateResponse,
    CardListResponse,
    CardRating,
    CardStatus,
    NextCardResponse,
    RateCardResponse,
} from '../types/api';
import { httpClient } from './httpClient';

interface FetchCardsParams {
    deckId: string;
    status?: CardStatus | null;
    search?: string;
    limit?: number;
    offset?: number;
}

export const fetchCards = async (params: FetchCardsParams): Promise<CardListResponse> => {
    const response = await httpClient.get<CardListResponse>('/cards', {
        params: {
            deck_id: params.deckId,
            status: params.status ?? undefined,
            search: params.search,
            limit: params.limit,
            offset: params.offset,
        },
    });

    return response.data;
};

export const createCards = async (payload: {
    deck_id: string;
    words: string[];
}): Promise<CardCreateResponse> => {
    const response = await httpClient.post<CardCreateResponse>('/cards', payload);
    return response.data;
};

export const getNextCard = async (deckId?: string | null): Promise<NextCardResponse | null> => {
    const response = await httpClient.get<NextCardResponse>('/cards/next', {
        validateStatus: (status) => status === 200 || status === 204,
        params: { deck_id: deckId ?? undefined },
    });

    if (response.status === 204) {
        return null;
    }

    return response.data;
};

export const rateCard = async (payload: {
    card_id: string;
    rating: CardRating;
    duration_seconds?: number;
}): Promise<RateCardResponse> => {
    const response = await httpClient.post<RateCardResponse>('/cards/rate', payload);
    return response.data;
};
