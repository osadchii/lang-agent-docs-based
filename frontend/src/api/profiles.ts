import { httpClient } from './httpClient';
import type {
    LanguageProfile,
    LanguageProfileCreatePayload,
    LanguageProfileListResponse,
    LanguageProfileUpdatePayload,
} from '../types/api';

export async function fetchProfiles(): Promise<LanguageProfile[]> {
    const { data } = await httpClient.get<LanguageProfileListResponse>('/profiles');
    return data.data;
}

export async function createProfile(
    payload: LanguageProfileCreatePayload,
): Promise<LanguageProfile> {
    const { data } = await httpClient.post<LanguageProfile>('/profiles', payload);
    return data;
}

export async function updateProfile(
    profileId: string,
    payload: LanguageProfileUpdatePayload,
): Promise<LanguageProfile> {
    const { data } = await httpClient.patch<LanguageProfile>(`/profiles/${profileId}`, payload);
    return data;
}

export async function deleteProfile(profileId: string): Promise<void> {
    await httpClient.delete(`/profiles/${profileId}`);
}

export async function activateProfile(profileId: string): Promise<LanguageProfile> {
    const { data } = await httpClient.post<LanguageProfile>(`/profiles/${profileId}/activate`);
    return data;
}
