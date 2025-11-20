import MockAdapter from 'axios-mock-adapter';
import { beforeEach, describe, expect, it } from 'vitest';
import { httpClient } from './httpClient';
import { fetchCalendar, fetchStats, fetchStreak } from './stats';

const statsResponse = {
    profile_id: 'profile-id',
    language: 'es',
    current_level: 'B1',
    period: 'month' as const,
    streak: {
        current: 5,
        best: 14,
        total_days: 24,
    },
    cards: {
        total: 120,
        studied: 90,
        new: 30,
        stats: { know: 40, repeat: 10, dont_know: 5 },
    },
    exercises: {
        total: 18,
        stats: { correct: 10, partial: 4, incorrect: 4 },
        accuracy: 0.77,
    },
    time: {
        total_minutes: 320,
        average_per_day: 12,
    },
    activity: [
        {
            date: '2025-01-01',
            cards_studied: 4,
            exercises_completed: 1,
            time_minutes: 8,
            activity_level: 'medium' as const,
        },
    ],
};

describe('stats API client', () => {
    const mock = new MockAdapter(httpClient);

    beforeEach(() => {
        mock.reset();
    });

    it('fetchStats forwards params and returns payload', async () => {
        mock.onGet('/stats').reply((config) => {
            expect(config.params?.profile_id).toBe('profile-id');
            expect(config.params?.period).toBe('week');
            return [200, statsResponse];
        });

        const response = await fetchStats({ profileId: 'profile-id', period: 'week' });
        expect(response.profile_id).toBe('profile-id');
        expect(response.streak.current).toBe(5);
    });

    it('fetchStreak hits streak endpoint', async () => {
        mock.onGet('/stats/streak').reply((config) => {
            expect(config.params?.profile_id).toBe('profile-id');
            return [
                200,
                {
                    profile_id: 'profile-id',
                    current_streak: 3,
                    best_streak: 10,
                    total_active_days: 15,
                    today_completed: true,
                    last_activity: '2025-01-01T12:00:00Z',
                    streak_safe_until: '2025-01-02T00:00:00Z',
                },
            ];
        });

        const response = await fetchStreak('profile-id');
        expect(response.today_completed).toBe(true);
        expect(response.total_active_days).toBe(15);
    });

    it('fetchCalendar uses optional params', async () => {
        mock.onGet('/stats/calendar').reply((config) => {
            expect(config.params?.profile_id).toBeUndefined();
            expect(config.params?.weeks).toBe(8);
            return [
                200,
                {
                    data: [
                        {
                            date: '2025-01-02',
                            cards_studied: 2,
                            exercises_completed: 0,
                            time_minutes: 5,
                            activity_level: 'low',
                        },
                    ],
                },
            ];
        });

        const response = await fetchCalendar({ weeks: 8 });
        expect(response.data).toHaveLength(1);
        expect(response.data[0].cards_studied).toBe(2);
    });
});
