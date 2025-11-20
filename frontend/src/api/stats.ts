import type { CalendarResponse, StatsPeriod, StatsResponse, StreakResponse } from '../types/api';
import { httpClient } from './httpClient';

interface FetchStatsParams {
    profileId?: string | null;
    period?: StatsPeriod;
}

interface FetchCalendarParams {
    profileId?: string | null;
    weeks?: number;
}

export const fetchStats = async (params: FetchStatsParams = {}): Promise<StatsResponse> => {
    const response = await httpClient.get<StatsResponse>('/stats', {
        params: {
            profile_id: params.profileId ?? undefined,
            period: params.period,
        },
    });

    return response.data;
};

export const fetchStreak = async (profileId: string | null = null): Promise<StreakResponse> => {
    const response = await httpClient.get<StreakResponse>('/stats/streak', {
        params: { profile_id: profileId ?? undefined },
    });

    return response.data;
};

export const fetchCalendar = async (
    params: FetchCalendarParams = {},
): Promise<CalendarResponse> => {
    const response = await httpClient.get<CalendarResponse>('/stats/calendar', {
        params: {
            profile_id: params.profileId ?? undefined,
            weeks: params.weeks,
        },
    });

    return response.data;
};
