import MockAdapter from 'axios-mock-adapter';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import {
    httpClient,
    resetHttpAuthState,
    setAuthToken,
    setTokenRefresher,
    setUnauthorizedHandler,
} from './httpClient';

describe('httpClient', () => {
    const mock = new MockAdapter(httpClient);

    beforeEach(() => {
        mock.reset();
        resetHttpAuthState();
    });

    it('exposes sane default configuration', () => {
        expect(httpClient.defaults.baseURL).toBe('http://localhost:8000/api');
        expect(httpClient.defaults.timeout).toBe(10000);
    });

    it('attaches Authorization header when token is present', async () => {
        setAuthToken('abc123');

        mock.onGet('/ping').reply((config) => {
            expect(config.headers?.Authorization).toBe('Bearer abc123');
            return [200, { ok: true }];
        });

        await httpClient.get('/ping');
    });

    it('skips Authorization header when skipAuth flag is true', async () => {
        setAuthToken('abc123');

        mock.onGet('/public').reply((config) => {
            expect(config.headers?.Authorization).toBeUndefined();
            return [200, { ok: true }];
        });

        await httpClient.get('/public', { skipAuth: true });
    });

    it('does not set Authorization header when token is absent', async () => {
        mock.onGet('/ping').reply((config) => {
            expect(config.headers?.Authorization).toBeUndefined();
            return [200, { ok: true }];
        });

        await httpClient.get('/ping');
    });

    it('refreshes token on 401 responses and retries once', async () => {
        setAuthToken('expired');
        setTokenRefresher(async () => 'fresh-token');

        mock.onGet('/secure')
            .replyOnce(401)
            .onGet('/secure')
            .replyOnce((config) => {
                expect(config.headers?.Authorization).toBe('Bearer fresh-token');
                return [200, { ok: true }];
            });

        const response = await httpClient.get('/secure');
        expect(response.status).toBe(200);
        expect(response.data).toEqual({ ok: true });
    });

    it('propagates ApiError and triggers unauthorized handler when refresh fails', async () => {
        const onUnauthorized = vi.fn();
        setAuthToken('expired');
        setTokenRefresher(async () => null);
        setUnauthorizedHandler(onUnauthorized);

        mock.onGet('/secure').reply(401);

        await expect(httpClient.get('/secure')).rejects.toMatchObject({
            name: 'ApiError',
            status: 401,
        });
        expect(onUnauthorized).toHaveBeenCalledTimes(1);
    });
});
