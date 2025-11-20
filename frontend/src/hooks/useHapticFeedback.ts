import { useCallback } from 'react';
import { useTelegram } from './useTelegram';

type ImpactStyle = 'light' | 'medium' | 'heavy' | 'rigid' | 'soft';
type NotificationStyle = 'error' | 'success' | 'warning';

/**
 * Thin helper around Telegram HapticFeedback API.
 * Falls back silently in browser mode.
 */
export const useHapticFeedback = () => {
    const { webApp } = useTelegram();

    const impact = useCallback(
        (style: ImpactStyle = 'light') => {
            webApp?.HapticFeedback?.impactOccurred(style);
        },
        [webApp],
    );

    const notify = useCallback(
        (type: NotificationStyle) => {
            webApp?.HapticFeedback?.notificationOccurred(type);
        },
        [webApp],
    );

    const selectionChanged = useCallback(() => {
        webApp?.HapticFeedback?.selectionChanged();
    }, [webApp]);

    return {
        impact,
        notify,
        selectionChanged,
    };
};
