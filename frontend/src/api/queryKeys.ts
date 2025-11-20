export const queryKeys = {
    profiles: ['profiles'] as const,
    chatHistoryRoot: ['chatHistory'] as const,
    chatHistory: (profileId: string | null) => ['chatHistory', profileId ?? 'none'] as const,
    stats: (profileId: string | null) => ['stats', profileId ?? 'active'] as const,
    streak: (profileId: string | null) => ['streak', profileId ?? 'active'] as const,
    calendar: (profileId: string | null) => ['calendar', profileId ?? 'active'] as const,
    decks: (profileId: string | null) => ['decks', profileId ?? 'all'] as const,
    cards: (deckId: string) => ['cards', deckId] as const,
    nextCard: (deckId: string | null) => ['nextCard', deckId ?? 'active'] as const,
} as const;
