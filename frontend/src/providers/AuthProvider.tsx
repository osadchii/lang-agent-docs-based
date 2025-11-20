import { createContext, type PropsWithChildren, useContext, useMemo } from 'react';
import { useAuth, type UseAuthResult } from '../hooks/useAuth';
import { useTelegram } from '../hooks/useTelegram';

interface AuthContextValue extends UseAuthResult {
    initData: string | null;
    telegramReady: boolean;
}

const AuthContext = createContext<AuthContextValue>({
    initData: null,
    telegramReady: false,
    user: null,
    token: null,
    status: 'idle',
    error: null,
    isAuthenticated: false,
});

export const AuthProvider = ({ children }: PropsWithChildren) => {
    const { initData, isReady } = useTelegram();
    const auth = useAuth(isReady ? initData : null);

    const value = useMemo<AuthContextValue>(
        () => ({
            ...auth,
            initData: isReady && initData ? initData : null,
            telegramReady: isReady,
        }),
        [auth, initData, isReady],
    );

    return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};

// eslint-disable-next-line react-refresh/only-export-components
export const useAuthContext = () => useContext(AuthContext);
