import { useEffect } from 'react';
import { useTelegram } from './useTelegram';

interface MainButtonOptions {
    text?: string;
    color?: string;
    textColor?: string;
    isVisible?: boolean;
    isActive?: boolean;
    loading?: boolean;
    onClick?: () => void;
}

/**
 * Manages Telegram main button lifecycle for a screen.
 * Cleans up listeners and hides button on unmount.
 */
export const useMainButton = ({
    text,
    color,
    textColor,
    isVisible = true,
    isActive = true,
    loading = false,
    onClick,
}: MainButtonOptions) => {
    const { webApp } = useTelegram();

    useEffect(() => {
        if (!webApp) {
            return undefined;
        }

        const { MainButton } = webApp;

        if (text) {
            MainButton.setText(text);
        }

        MainButton.setParams({
            color,
            text_color: textColor,
            is_active: isActive,
            is_visible: isVisible,
        });

        if (loading) {
            MainButton.showProgress();
        } else {
            MainButton.hideProgress();
        }

        if (isVisible) {
            MainButton.show();
        } else {
            MainButton.hide();
        }

        if (isActive) {
            MainButton.enable();
        } else {
            MainButton.disable();
        }

        if (onClick) {
            MainButton.onClick(onClick);
        }

        return () => {
            if (onClick) {
                MainButton.offClick(onClick);
            }
            MainButton.hideProgress();
            MainButton.hide();
        };
    }, [webApp, text, color, textColor, isVisible, isActive, loading, onClick]);
};
