import type { MockedFunction } from 'vitest';
import { vi } from 'vitest';

vi.mock('../api/profiles', () => ({
    fetchProfiles: vi.fn(),
}));

vi.mock('./AuthProvider', () => ({
    useAuthContext: () => ({ isAuthenticated: true }),
}));

import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { act, renderHook, waitFor } from '@testing-library/react';
import type { PropsWithChildren } from 'react';
import { fetchProfiles } from '../api/profiles';
import { useOnboarding, OnboardingProvider } from './OnboardingProvider';
import type { LanguageProfile } from '../types/api';

const mockFetchProfiles = fetchProfiles as MockedFunction<typeof fetchProfiles>;

const createWrapper = () => {
    const client = new QueryClient({
        defaultOptions: {
            queries: {
                retry: false,
            },
        },
    });

    return ({ children }: PropsWithChildren) => (
        <QueryClientProvider client={client}>
            <OnboardingProvider>{children}</OnboardingProvider>
        </QueryClientProvider>
    );
};

const activeProfile: LanguageProfile = {
    id: 'profile-1',
    user_id: 'user-1',
    language: 'en',
    language_name: 'English',
    current_level: 'B1',
    target_level: 'B2',
    goals: ['speaking'],
    interface_language: 'en',
    is_active: true,
    progress: {
        cards_count: 0,
        exercises_count: 0,
        streak: 0,
    },
    created_at: '2024-01-01T00:00:00Z',
    updated_at: '2024-01-01T00:00:00Z',
};

const inactiveProfile: LanguageProfile = {
    ...activeProfile,
    id: 'profile-2',
    is_active: false,
};

describe('OnboardingProvider', () => {
    beforeEach(() => {
        localStorage.clear();
        vi.clearAllMocks();
    });

    it('marks onboarding as completed when an active profile is present', async () => {
        mockFetchProfiles.mockResolvedValue([activeProfile]);
        const wrapper = createWrapper();
        const { result } = renderHook(() => useOnboarding(), { wrapper });

        let refreshed = false;
        await act(async () => {
            refreshed = await result.current.refreshStatus();
        });

        expect(mockFetchProfiles).toHaveBeenCalledTimes(1);
        expect(refreshed).toBe(true);
        expect(localStorage.getItem('lang-agent:onboarding-complete')).toBe('true');
        expect(result.current.completed).toBe(true);
    });

    it('refreshStatus updates completion after profile activation', async () => {
        mockFetchProfiles.mockResolvedValueOnce([inactiveProfile]);
        const wrapper = createWrapper();
        const { result } = renderHook(() => useOnboarding(), { wrapper });

        let refreshed = false;
        await act(async () => {
            refreshed = await result.current.refreshStatus();
        });

        expect(refreshed).toBe(false);
        expect(result.current.completed).toBe(false);

        mockFetchProfiles.mockResolvedValueOnce([inactiveProfile, activeProfile]);

        await act(async () => {
            refreshed = await result.current.refreshStatus();
        });

        expect(mockFetchProfiles).toHaveBeenCalledTimes(2);
        expect(refreshed).toBe(true);
        await waitFor(() => expect(result.current.completed).toBe(true));
    });
});
