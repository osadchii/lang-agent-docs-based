import MockAdapter from 'axios-mock-adapter';
import { describe, expect, it, beforeEach } from 'vitest';
import { httpClient, setAuthToken } from './httpClient';

describe('httpClient', () => {
    const mock = new MockAdapter(httpClient);

    beforeEach(() => {
        mock.reset();
        setAuthToken(null);
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

    it('does not set Authorization header when token is absent', async () => {
        mock.onGet('/ping').reply((config) => {
            expect(config.headers?.Authorization).toBeUndefined();
            return [200, { ok: true }];
        });

        await httpClient.get('/ping');
    });
});
