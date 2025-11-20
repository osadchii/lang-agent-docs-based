/**
 * Custom React hook for Telegram WebApp integration
 * Provides access to Telegram WebApp API and user data
 */

import { startTransition, useEffect, useState } from 'react';
import type { TelegramWebApp, TelegramUser, ThemeParams } from '../types/telegram';

interface UseTelegramReturn {
    webApp: TelegramWebApp | null;
    user: TelegramUser | null;
    initData: string;
    colorScheme: 'light' | 'dark';
    platform: string;
    isReady: boolean;
    themeParams: ThemeParams | null;
}

export const useTelegram = (): UseTelegramReturn => {
    const [isReady, setIsReady] = useState(false);
    const [webApp, setWebApp] = useState<TelegramWebApp | null>(null);
    const [themeParams, setThemeParams] = useState<ThemeParams | null>(null);
    const [colorScheme, setColorScheme] = useState<'light' | 'dark'>('dark');

    useEffect(() => {
        const tg = window.Telegram?.WebApp;

        if (tg) {
            // Initialize Telegram WebApp
            tg.ready();
            tg.expand();

            // Enable closing confirmation (optional, comment if not needed)
            // tg.enableClosingConfirmation();

            // Set theme colors (закатная палитра)
            tg.setHeaderColor('#0A0E27');
            tg.setBackgroundColor('#0A0E27');

            const syncTheme = () => {
                setThemeParams({ ...tg.themeParams });
                setColorScheme(tg.colorScheme || 'dark');
            };

            startTransition(() => {
                setWebApp(tg);
                setIsReady(true);
                syncTheme();
            });

            tg.onEvent('themeChanged', syncTheme);

            console.log('Telegram WebApp initialized:', {
                version: tg.version,
                platform: tg.platform,
                colorScheme: tg.colorScheme,
                user: tg.initDataUnsafe.user,
            });

            return () => {
                tg.offEvent('themeChanged', syncTheme);
            };
        } else {
            console.warn('Telegram WebApp is not available. Running in browser mode.');
            // For development: create mock data
            if (import.meta.env.DEV) {
                const mockWebApp = createMockWebApp();
                startTransition(() => {
                    setWebApp(mockWebApp);
                    setIsReady(true);
                    setThemeParams(mockWebApp.themeParams);
                    setColorScheme(mockWebApp.colorScheme);
                });
            } else {
                startTransition(() => {
                    setIsReady(true);
                });
            }
        }
    }, []);

    return {
        webApp,
        user: webApp?.initDataUnsafe.user || null,
        initData: webApp?.initData || '',
        colorScheme,
        platform: webApp?.platform || 'unknown',
        isReady,
        themeParams,
    };
};

/**
 * Mock Telegram WebApp for development purposes
 */
function createMockWebApp(): TelegramWebApp {
    return {
        initData: 'mock_init_data',
        initDataUnsafe: {
            user: {
                id: 123456789,
                first_name: 'Test',
                last_name: 'User',
                username: 'testuser',
                language_code: 'ru',
            },
            auth_date: Date.now(),
            hash: 'mock_hash',
        },
        version: '7.0',
        platform: 'web',
        colorScheme: 'dark',
        themeParams: {
            bg_color: '#0A0E27',
            text_color: '#FFFFFF',
            hint_color: '#B0B3C1',
            link_color: '#FF6B35',
            button_color: '#FF6B35',
            button_text_color: '#FFFFFF',
            secondary_bg_color: '#1A1D35',
        },
        isExpanded: true,
        viewportHeight: 600,
        viewportStableHeight: 600,
        headerColor: '#0A0E27',
        backgroundColor: '#0A0E27',
        isClosingConfirmationEnabled: false,
        BackButton: {
            isVisible: false,
            show: () => console.log('BackButton.show()'),
            hide: () => console.log('BackButton.hide()'),
            onClick: (callback: () => void) => console.log('BackButton.onClick()', callback),
            offClick: (callback: () => void) => console.log('BackButton.offClick()', callback),
        },
        MainButton: {
            text: '',
            color: '#FF6B35',
            textColor: '#FFFFFF',
            isVisible: false,
            isActive: true,
            isProgressVisible: false,
            setText: (text: string) => console.log('MainButton.setText()', text),
            onClick: (callback: () => void) => console.log('MainButton.onClick()', callback),
            offClick: (callback: () => void) => console.log('MainButton.offClick()', callback),
            show: () => console.log('MainButton.show()'),
            hide: () => console.log('MainButton.hide()'),
            enable: () => console.log('MainButton.enable()'),
            disable: () => console.log('MainButton.disable()'),
            showProgress: () => console.log('MainButton.showProgress()'),
            hideProgress: () => console.log('MainButton.hideProgress()'),
            setParams: (params: unknown) => console.log('MainButton.setParams()', params),
        },
        HapticFeedback: {
            impactOccurred: (style: string) =>
                console.log('HapticFeedback.impactOccurred()', style),
            notificationOccurred: (type: string) =>
                console.log('HapticFeedback.notificationOccurred()', type),
            selectionChanged: () => console.log('HapticFeedback.selectionChanged()'),
        },
        CloudStorage: {
            setItem: (key: string, value: string, callback?: (error: Error | null) => void) => {
                console.log('CloudStorage.setItem()', key, value);
                callback?.(null);
            },
            getItem: (key: string, callback: (error: Error | null, value?: string) => void) => {
                console.log('CloudStorage.getItem()', key);
                callback(null, '');
            },
            getItems: (
                keys: string[],
                callback: (error: Error | null, values?: Record<string, string>) => void,
            ) => {
                console.log('CloudStorage.getItems()', keys);
                callback(null, {});
            },
            removeItem: (key: string, callback?: (error: Error | null) => void) => {
                console.log('CloudStorage.removeItem()', key);
                callback?.(null);
            },
            removeItems: (keys: string[], callback?: (error: Error | null) => void) => {
                console.log('CloudStorage.removeItems()', keys);
                callback?.(null);
            },
            getKeys: (callback: (error: Error | null, keys?: string[]) => void) => {
                console.log('CloudStorage.getKeys()');
                callback(null, []);
            },
        },
        ready: () => console.log('WebApp.ready()'),
        expand: () => console.log('WebApp.expand()'),
        close: () => console.log('WebApp.close()'),
        enableClosingConfirmation: () => console.log('WebApp.enableClosingConfirmation()'),
        disableClosingConfirmation: () => console.log('WebApp.disableClosingConfirmation()'),
        setHeaderColor: (color: string) => console.log('WebApp.setHeaderColor()', color),
        setBackgroundColor: (color: string) => console.log('WebApp.setBackgroundColor()', color),
        onEvent: (eventType: string, callback: () => void) =>
            console.log('WebApp.onEvent()', eventType, callback),
        offEvent: (eventType: string, callback: () => void) =>
            console.log('WebApp.offEvent()', eventType, callback),
        sendData: (data: string) => console.log('WebApp.sendData()', data),
        openLink: (url: string) => console.log('WebApp.openLink()', url),
        openTelegramLink: (url: string) => console.log('WebApp.openTelegramLink()', url),
        showPopup: (params: unknown, callback?: (buttonId: string) => void) =>
            console.log('WebApp.showPopup()', params, callback),
        showAlert: (message: string, callback?: () => void) =>
            console.log('WebApp.showAlert()', message, callback),
        showConfirm: (message: string, callback?: (confirmed: boolean) => void) =>
            console.log('WebApp.showConfirm()', message, callback),
    };
}
