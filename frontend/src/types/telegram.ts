/**
 * TypeScript definitions for Telegram WebApp API
 * https://core.telegram.org/bots/webapps
 */

export interface TelegramUser {
    id: number;
    first_name: string;
    last_name?: string;
    username?: string;
    language_code?: string;
    is_premium?: boolean;
    photo_url?: string;
}

export interface TelegramWebAppInitData {
    query_id?: string;
    user?: TelegramUser;
    receiver?: TelegramUser;
    chat?: {
        id: number;
        type: string;
        title: string;
        username?: string;
        photo_url?: string;
    };
    chat_type?: string;
    chat_instance?: string;
    start_param?: string;
    can_send_after?: number;
    auth_date: number;
    hash: string;
}

export interface ThemeParams {
    bg_color?: string;
    text_color?: string;
    hint_color?: string;
    link_color?: string;
    button_color?: string;
    button_text_color?: string;
    secondary_bg_color?: string;
}

export interface BackButton {
    isVisible: boolean;
    show(): void;
    hide(): void;
    onClick(callback: () => void): void;
    offClick(callback: () => void): void;
}

export interface MainButton {
    text: string;
    color: string;
    textColor: string;
    isVisible: boolean;
    isActive: boolean;
    isProgressVisible: boolean;
    setText(text: string): void;
    onClick(callback: () => void): void;
    offClick(callback: () => void): void;
    show(): void;
    hide(): void;
    enable(): void;
    disable(): void;
    showProgress(leaveActive?: boolean): void;
    hideProgress(): void;
    setParams(params: {
        text?: string;
        color?: string;
        text_color?: string;
        is_active?: boolean;
        is_visible?: boolean;
    }): void;
}

export interface HapticFeedback {
    impactOccurred(style: 'light' | 'medium' | 'heavy' | 'rigid' | 'soft'): void;
    notificationOccurred(type: 'error' | 'success' | 'warning'): void;
    selectionChanged(): void;
}

export interface CloudStorage {
    setItem(key: string, value: string, callback?: (error: Error | null) => void): void;
    getItem(key: string, callback: (error: Error | null, value?: string) => void): void;
    getItems(
        keys: string[],
        callback: (error: Error | null, values?: Record<string, string>) => void,
    ): void;
    removeItem(key: string, callback?: (error: Error | null) => void): void;
    removeItems(keys: string[], callback?: (error: Error | null) => void): void;
    getKeys(callback: (error: Error | null, keys?: string[]) => void): void;
}

export interface TelegramWebApp {
    initData: string;
    initDataUnsafe: TelegramWebAppInitData;
    version: string;
    platform: string;
    colorScheme: 'light' | 'dark';
    themeParams: ThemeParams;
    isExpanded: boolean;
    viewportHeight: number;
    viewportStableHeight: number;
    headerColor: string;
    backgroundColor: string;
    isClosingConfirmationEnabled: boolean;

    BackButton: BackButton;
    MainButton: MainButton;
    HapticFeedback: HapticFeedback;
    CloudStorage: CloudStorage;

    ready(): void;
    expand(): void;
    close(): void;
    enableClosingConfirmation(): void;
    disableClosingConfirmation(): void;
    setHeaderColor(color: string): void;
    setBackgroundColor(color: string): void;
    onEvent(eventType: string, callback: () => void): void;
    offEvent(eventType: string, callback: () => void): void;
    sendData(data: string): void;
    openLink(url: string): void;
    openTelegramLink(url: string): void;
    showPopup(
        params: {
            title?: string;
            message: string;
            buttons: Array<{ id?: string; type: string; text?: string }>;
        },
        callback?: (buttonId: string) => void,
    ): void;
    showAlert(message: string, callback?: () => void): void;
    showConfirm(message: string, callback?: (confirmed: boolean) => void): void;
}

declare global {
    interface Window {
        Telegram?: {
            WebApp: TelegramWebApp;
        };
    }
}

export {};
