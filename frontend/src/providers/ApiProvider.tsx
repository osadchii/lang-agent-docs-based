import { QueryClientProvider } from '@tanstack/react-query';
import { type PropsWithChildren, useState } from 'react';
import { createQueryClient } from '../api/queryClient';

export const ApiProvider = ({ children }: PropsWithChildren) => {
    const [client] = useState(() => createQueryClient());

    return <QueryClientProvider client={client}>{children}</QueryClientProvider>;
};
