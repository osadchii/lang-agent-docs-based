import axios, { type AxiosError, type InternalAxiosRequestConfig } from 'axios';
import { toApiError } from './errors';

declare module 'axios' {
    export interface AxiosRequestConfig {
        skipAuth?: boolean;
        _retry?: boolean;
    }
}

const baseURL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000/api';
const defaultTimeout = Number(import.meta.env.VITE_API_TIMEOUT ?? '10000');

let authToken: string | null = null;
let refreshHandler: (() => Promise<string | null>) | null = null;
let unauthorizedHandler: (() => void) | null = null;
let refreshPromise: Promise<string | null> | null = null;

const parseTimeout = () => (Number.isNaN(defaultTimeout) ? 10000 : defaultTimeout);

export const setAuthToken = (token: string | null): void => {
    authToken = token;
};

export const setTokenRefresher = (handler: (() => Promise<string | null>) | null): void => {
    refreshHandler = handler;
};

export const setUnauthorizedHandler = (handler: (() => void) | null): void => {
    unauthorizedHandler = handler;
};

export const resetHttpAuthState = (): void => {
    authToken = null;
    refreshHandler = null;
    unauthorizedHandler = null;
    refreshPromise = null;
};

const refreshAccessToken = async (): Promise<string | null> => {
    if (!refreshHandler) {
        return null;
    }

    if (!refreshPromise) {
        refreshPromise = refreshHandler()
            .then((token) => {
                if (token) {
                    authToken = token;
                }
                return token;
            })
            .catch(() => null)
            .finally(() => {
                refreshPromise = null;
            });
    }

    return refreshPromise;
};

export const httpClient = axios.create({
    baseURL,
    timeout: parseTimeout(),
});

httpClient.interceptors.request.use((config) => {
    const nextConfig = { ...config };
    if (!nextConfig.headers) {
        nextConfig.headers = {};
    }
    if (authToken && !nextConfig.skipAuth) {
        nextConfig.headers.Authorization = `Bearer ${authToken}`;
    }
    const headers = nextConfig.headers as Record<string, string>;
    headers.Accept = headers.Accept ?? 'application/json';
    return nextConfig;
});

const handleError = async (error: AxiosError) => {
    const apiError = toApiError(error);
    const requestConfig = error.config as InternalAxiosRequestConfig | undefined;

    const shouldAttemptRefresh =
        error.response?.status === 401 &&
        requestConfig &&
        !requestConfig._retry &&
        !requestConfig.skipAuth;

    if (shouldAttemptRefresh) {
        requestConfig._retry = true;
        const newToken = await refreshAccessToken();

        if (newToken && requestConfig.headers) {
            requestConfig.headers.Authorization = `Bearer ${newToken}`;
            return httpClient(requestConfig);
        }

        unauthorizedHandler?.();
    }

    return Promise.reject(apiError);
};

httpClient.interceptors.response.use((response) => response, handleError);
