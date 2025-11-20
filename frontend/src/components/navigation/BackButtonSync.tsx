import { useCallback, useEffect, useMemo } from 'react';
import { useLocation, useMatches, useNavigate } from 'react-router-dom';
import { useTelegram } from '../../hooks/useTelegram';
import type { AppRouteHandle } from '../../router/types';

const ROOT_PATHS = new Set([
    '/',
    '/practice',
    '/practice/cards',
    '/practice/exercises',
    '/groups',
    '/profile',
]);

const normalizePath = (path: string) =>
    path.endsWith('/') && path.length > 1 ? path.slice(0, -1) : path;

export const BackButtonSync = () => {
    const { webApp } = useTelegram();
    const location = useLocation();
    const matches = useMatches();
    const navigate = useNavigate();

    const hideBackButton = useMemo(
        () =>
            matches.some((match) => {
                const handle = match.handle as AppRouteHandle | undefined;
                return handle?.hideBackButton;
            }),
        [matches],
    );

    const customBack = useMemo(() => {
        for (let index = matches.length - 1; index >= 0; index -= 1) {
            const handle = matches[index].handle as AppRouteHandle | undefined;
            if (handle?.onBack) {
                return handle.onBack;
            }
        }
        return undefined;
    }, [matches]);

    const historyIndex = typeof window !== 'undefined' ? (window.history.state?.idx ?? 0) : 0;
    const normalizedPath = normalizePath(location.pathname);
    const isRootPath = ROOT_PATHS.has(normalizedPath);
    const shouldShowBack =
        !hideBackButton && (!isRootPath || historyIndex > 0 || Boolean(customBack));

    const handleBack = useCallback(() => {
        if (customBack) {
            customBack();
            return;
        }
        navigate(-1);
    }, [customBack, navigate]);

    useEffect(() => {
        if (!webApp) {
            return undefined;
        }

        if (!shouldShowBack) {
            webApp.BackButton.hide();
            return undefined;
        }

        webApp.BackButton.show();
        webApp.BackButton.onClick(handleBack);

        return () => {
            webApp.BackButton.offClick(handleBack);
            webApp.BackButton.hide();
        };
    }, [webApp, shouldShowBack, handleBack]);

    return null;
};
