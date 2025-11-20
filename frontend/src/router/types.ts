export interface AppRouteHandle {
    hideBottomNav?: boolean;
    hideBackButton?: boolean;
    /**
     * Optional custom back handler for Telegram BackButton.
     * If not provided, history.back() is used.
     */
    onBack?: () => void;
}
