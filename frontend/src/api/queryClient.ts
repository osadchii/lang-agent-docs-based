import { QueryClient } from '@tanstack/react-query';
import { isRetryableError } from './errors';

export const createQueryClient = () =>
    new QueryClient({
        defaultOptions: {
            queries: {
                staleTime: 2 * 60 * 1000,
                gcTime: 10 * 60 * 1000,
                refetchOnWindowFocus: false,
                retry: (failureCount, error) => failureCount < 2 && isRetryableError(error),
            },
            mutations: {
                retry: 0,
            },
        },
    });

export const queryClient = createQueryClient();
