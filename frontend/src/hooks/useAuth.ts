import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { validateInitData } from '../api/auth';
import { setAuthToken, setTokenRefresher, setUnauthorizedHandler } from '../api/httpClient';
import type { ApiUser } from '../types/api';

type AuthStatus = 'idle' | 'loading' | 'success' | 'error';

export interface UseAuthResult {
    user: ApiUser | null;
    token: string | null;
    status: AuthStatus;
    error: string | null;
    isAuthenticated: boolean;
}

export const useAuth = (initData: string | null): UseAuthResult => {
    const [user, setUser] = useState<ApiUser | null>(null);
    const [token, setToken] = useState<string | null>(null);
    const [status, setStatus] = useState<AuthStatus>('idle');
    const [error, setError] = useState<string | null>(null);
    const mountedRef = useRef(true);

    useEffect(() => {
        return () => {
            mountedRef.current = false;
        };
    }, []);

    const refreshSession = useCallback(async (): Promise<string | null> => {
        if (!initData) {
            return null;
        }

        const response = await validateInitData(initData);

        if (!mountedRef.current) {
            return response.token;
        }

        setUser(response.user);
        setToken(response.token);
        setAuthToken(response.token);

        return response.token;
    }, [initData]);

    useEffect(() => {
        if (!initData) {
            return;
        }

        let isCancelled = false;

        const authenticate = async () => {
            setStatus('loading');
            setError(null);

            try {
                await refreshSession();
                if (!isCancelled) {
                    setStatus('success');
                }
            } catch (err) {
                console.error('Auth failed', err);
                if (isCancelled) {
                    return;
                }
                setAuthToken(null);
                setError('Не удалось авторизоваться. Попробуйте открыть Mini App заново.');
                setStatus('error');
            }
        };

        authenticate();

        return () => {
            isCancelled = true;
        };
    }, [initData, refreshSession]);

    useEffect(() => {
        setTokenRefresher(initData ? () => refreshSession() : null);
        setUnauthorizedHandler(() => {
            if (!mountedRef.current) {
                return;
            }
            setStatus('error');
            setError('Сессия истекла. Откройте Mini App заново, чтобы продолжить.');
            setUser(null);
            setToken(null);
            setAuthToken(null);
        });

        return () => {
            setTokenRefresher(null);
            setUnauthorizedHandler(null);
        };
    }, [initData, refreshSession]);

    return useMemo(
        () => ({
            user,
            token,
            status,
            error,
            isAuthenticated: status === 'success',
        }),
        [user, token, status, error],
    );
};
