import { useEffect, useMemo, useState } from 'react';
import { validateInitData } from '../api/auth';
import { setAuthToken } from '../api/httpClient';
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

  useEffect(() => {
    if (!initData) {
      return;
    }

    let isCancelled = false;

    const authenticate = async () => {
      setStatus('loading');
      setError(null);

      try {
        const response = await validateInitData(initData);
        if (isCancelled) {
          return;
        }

        setUser(response.user);
        setToken(response.token);
        setAuthToken(response.token);
        setStatus('success');
      } catch (err) {
        console.error('Auth failed', err);
        if (isCancelled) {
          return;
        }
        setError('Не удалось авторизоваться. Попробуйте открыть Mini App заново.');
        setStatus('error');
      }
    };

    authenticate();

    return () => {
      isCancelled = true;
    };
  }, [initData]);

  return useMemo(
    () => ({
      user,
      token,
      status,
      error,
      isAuthenticated: status === 'success',
    }),
    [user, token, status, error]
  );
};
