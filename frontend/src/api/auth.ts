import type { AxiosRequestConfig } from 'axios';
import { httpClient } from './httpClient';
import type { ValidateInitDataResponse } from '../types/api';

export async function validateInitData(
    initData: string,
    config: AxiosRequestConfig = {},
): Promise<ValidateInitDataResponse> {
    const { data } = await httpClient.post<ValidateInitDataResponse>(
        '/auth/validate',
        { init_data: initData },
        { skipAuth: true, ...config },
    );
    return data;
}
