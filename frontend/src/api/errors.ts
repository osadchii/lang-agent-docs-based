import { AxiosError } from 'axios';

const isAxiosError = (error: unknown): error is AxiosError =>
    typeof error === 'object' &&
    error !== null &&
    'isAxiosError' in error &&
    (error as AxiosError).isAxiosError === true;

interface ErrorPayload {
    code?: string;
    message?: string;
    details?: unknown;
}

interface ErrorResponseBody {
    error?: ErrorPayload;
}

export class ApiError extends Error {
    status: number | null;
    code?: string;
    details?: unknown;
    isNetworkError: boolean;
    isAuthError: boolean;

    constructor(
        message: string,
        options: {
            status: number | null;
            code?: string;
            details?: unknown;
            isNetworkError?: boolean;
            isAuthError?: boolean;
            cause?: unknown;
        },
    ) {
        super(message, { cause: options.cause });
        this.name = 'ApiError';
        this.status = options.status;
        this.code = options.code;
        this.details = options.details;
        this.isNetworkError = options.isNetworkError ?? false;
        this.isAuthError = options.isAuthError ?? false;
        Object.setPrototypeOf(this, ApiError.prototype);
    }
}

export const toApiError = (error: unknown): ApiError => {
    if (error instanceof ApiError) {
        return error;
    }

    if (isAxiosError(error)) {
        const status = error.response?.status ?? null;
        const payload = (error.response?.data ?? {}) as ErrorResponseBody;
        const message =
            payload.error?.message ??
            error.message ??
            'Не удалось выполнить запрос. Попробуйте позже.';

        return new ApiError(message, {
            status,
            code: payload.error?.code,
            details: payload.error?.details,
            isNetworkError: !error.response,
            isAuthError: status === 401,
            cause: error,
        });
    }

    return new ApiError(
        'Что-то пошло не так. Проверьте подключение к интернету и попробуйте ещё раз.',
        {
            status: null,
            code: 'UNKNOWN',
            details: error,
            isNetworkError: false,
            isAuthError: false,
        },
    );
};

export const getErrorMessage = (error: unknown, fallback = 'Не удалось выполнить действие.') =>
    toApiError(error).message || fallback;

export const isRetryableError = (error: unknown): boolean => {
    const apiError = toApiError(error);

    if (apiError.isAuthError) {
        return false;
    }

    if (apiError.isNetworkError) {
        return true;
    }

    return typeof apiError.status === 'number' ? apiError.status >= 500 : false;
};
