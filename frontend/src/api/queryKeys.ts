export const queryKeys = {
    profiles: ['profiles'] as const,
    chatHistoryRoot: ['chatHistory'] as const,
    chatHistory: (profileId: string | null) => ['chatHistory', profileId ?? 'none'] as const,
} as const;
