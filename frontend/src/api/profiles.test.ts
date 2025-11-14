import MockAdapter from 'axios-mock-adapter';
import { beforeEach, describe, expect, it } from 'vitest';

import { httpClient } from './httpClient';
import {
    activateProfile,
    createProfile,
    deleteProfile,
    fetchProfiles,
    updateProfile,
} from './profiles';

const profileResponse = {
    id: 'profile-id',
    user_id: 'user-id',
    language: 'es',
    language_name: 'Испанский',
    current_level: 'A2',
    target_level: 'B1',
    goals: ['travel'],
    interface_language: 'ru',
    is_active: true,
    progress: { cards_count: 0, exercises_count: 0, streak: 3 },
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
};

describe('profiles API client', () => {
    const mock = new MockAdapter(httpClient);

    beforeEach(() => {
        mock.reset();
    });

    it('fetchProfiles returns the server payload', async () => {
        mock.onGet('/profiles').reply(200, { data: [profileResponse] });

        const profiles = await fetchProfiles();
        expect(profiles).toHaveLength(1);
        expect(profiles[0].language).toBe('es');
    });

    it('createProfile posts payload to the backend', async () => {
        mock.onPost('/profiles').reply((config) => {
            const body = JSON.parse(config.data as string);
            expect(body.language).toBe('de');
            return [201, profileResponse];
        });

        const profile = await createProfile({
            language: 'de',
            current_level: 'A1',
            target_level: 'A2',
            goals: ['travel'],
            interface_language: 'ru',
        });

        expect(profile.language_name).toBe('Испанский');
    });

    it('activateProfile posts to the activate endpoint', async () => {
        mock.onPost('/profiles/profile-id/activate').reply(200, profileResponse);

        const profile = await activateProfile('profile-id');
        expect(profile.is_active).toBe(true);
    });

    it('updateProfile sends PATCH request', async () => {
        mock.onPatch('/profiles/profile-id').reply((config) => {
            const body = JSON.parse(config.data as string);
            expect(body.current_level).toBe('B1');
            return [200, profileResponse];
        });

        await updateProfile('profile-id', { current_level: 'B1' });
    });

    it('deleteProfile issues DELETE request', async () => {
        mock.onDelete('/profiles/profile-id').reply(204);

        await deleteProfile('profile-id');
    });
});
