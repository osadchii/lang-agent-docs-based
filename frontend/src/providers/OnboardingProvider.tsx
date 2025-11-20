import {
    createContext,
    type PropsWithChildren,
    useCallback,
    useContext,
    useMemo,
    useState,
} from 'react';

const STORAGE_KEY = 'lang-agent:onboarding-complete';

interface OnboardingContextValue {
    completed: boolean;
    markComplete: () => void;
    reset: () => void;
}

const OnboardingContext = createContext<OnboardingContextValue>({
    completed: false,
    markComplete: () => undefined,
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
    const [completed, setCompleted] = useState<boolean>(readInitialState);

    const markComplete = useCallback(() => {
        setCompleted(true);
        if (typeof window !== 'undefined') {
            window.localStorage.setItem(STORAGE_KEY, 'true');
        }
    }, []);

    const reset = useCallback(() => {
        setCompleted(false);
        if (typeof window !== 'undefined') {
            window.localStorage.setItem(STORAGE_KEY, 'false');
        }
    }, []);

    const value = useMemo(
        () => ({
            completed,
            markComplete,
            reset,
        }),
        [completed, markComplete, reset],
    );

    return <OnboardingContext.Provider value={value}>{children}</OnboardingContext.Provider>;
};

// eslint-disable-next-line react-refresh/only-export-components
export const useOnboarding = () => useContext(OnboardingContext);
