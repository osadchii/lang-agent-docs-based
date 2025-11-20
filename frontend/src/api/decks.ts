import type { Deck, DeckListResponse } from '../types/api';
import { httpClient } from './httpClient';

export const fetchDecks = async (
    profileId: string | null = null,
    includeGroup = true,
): Promise<Deck[]> => {
    const response = await httpClient.get<DeckListResponse>('/decks', {
        params: {
            profile_id: profileId ?? undefined,
            include_group: includeGroup,
        },
    });

    return response.data.data;
};
