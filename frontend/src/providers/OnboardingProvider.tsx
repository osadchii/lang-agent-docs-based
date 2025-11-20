import { useQuery, useQueryClient } from '@tanstack/react-query';
import {
    createContext,
    type PropsWithChildren,
    useCallback,
    useContext,
    useEffect,
    useMemo,
    useState,
} from 'react';
import { fetchProfiles } from '../api/profiles';
import { queryKeys } from '../api/queryKeys';
import type { LanguageProfile } from '../types/api';
import { useAuthContext } from './AuthProvider';

const STORAGE_KEY = 'lang-agent:onboarding-complete';

interface OnboardingContextValue {
    completed: boolean;
    checking: boolean;
    markComplete: () => void;
    refreshStatus: () => Promise<boolean>;
    reset: () => void;
}

const OnboardingContext = createContext<OnboardingContextValue>({
    completed: false,
    checking: false,
    markComplete: () => undefined,
    refreshStatus: async () => false,
    reset: () => undefined,
});

const readInitialState = () => {
    if (typeof window === 'undefined') {
        return false;
    }

    const stored = window.localStorage.getItem(STORAGE_KEY);
    if (stored === null) {
        return false;
    }

    return stored === 'true';
};

export const OnboardingProvider = ({ children }: PropsWithChildren) => {
    const { isAuthenticated } = useAuthContext();
    const queryClient = useQueryClient();
    const [completed, setCompleted] = useState<boolean>(readInitialState);
    const [checking, setChecking] = useState<boolean>(false);

    const persistState = useCallback((value: boolean) => {
        setCompleted(value);
        if (typeof window !== 'undefined') {
            window.localStorage.setItem(STORAGE_KEY, value ? 'true' : 'false');
        }
    }, []);

    const computeHasActiveProfile = useCallback(
        (profiles: LanguageProfile[]) => profiles.some((profile) => profile.is_active),
        [],
    );

    const evaluateProfiles = useCallback(
        (profiles: LanguageProfile[]) => {
            const hasActiveProfile = computeHasActiveProfile(profiles);
            persistState(hasActiveProfile);
            return hasActiveProfile;
        },
        [computeHasActiveProfile, persistState],
    );

    const profilesQuery = useQuery({
        queryKey: queryKeys.profiles,
        queryFn: fetchProfiles,
        enabled: isAuthenticated,
        staleTime: 60 * 1000,
        gcTime: 5 * 60 * 1000,
        refetchOnMount: false,
    });

    useEffect(() => {
        if (profilesQuery.data) {
            evaluateProfiles(profilesQuery.data);
        }
    }, [evaluateProfiles, profilesQuery.data]);

    const refreshStatus = useCallback(async () => {
        if (!isAuthenticated) {
            return completed;
        }

        setChecking(true);
        try {
            const result = await queryClient.fetchQuery({
                queryKey: queryKeys.profiles,
                queryFn: fetchProfiles,
            });
            return evaluateProfiles(result);
        } catch (error) {
            console.error('Failed to refresh onboarding status', error);
            return completed;
        } finally {
            setChecking(false);
        }
    }, [completed, evaluateProfiles, isAuthenticated, queryClient]);

    const markComplete = useCallback(() => {
        persistState(true);
    }, [persistState]);

    const reset = useCallback(() => {
        persistState(false);
    }, [persistState]);

    const value = useMemo(
        () => ({
            completed,
            checking:
                (isAuthenticated && (profilesQuery.isPending || profilesQuery.isRefetching)) ||
                checking,
            markComplete,
            refreshStatus,
            reset,
        }),
        [
            completed,
            checking,
            isAuthenticated,
            markComplete,
            profilesQuery.isPending,
            profilesQuery.isRefetching,
            refreshStatus,
            reset,
        ],
    );

    return <OnboardingContext.Provider value={value}>{children}</OnboardingContext.Provider>;
};

// eslint-disable-next-line react-refresh/only-export-components
export const useOnboarding = () => useContext(OnboardingContext);
