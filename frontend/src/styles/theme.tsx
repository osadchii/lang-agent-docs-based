import {
    createContext,
    type PropsWithChildren,
    useContext,
    useEffect,
    useMemo,
    useState,
} from 'react';
import { useTelegram } from '../hooks/useTelegram';
import {
    applyTheme,
    createTheme,
    defaultDarkTheme,
    type ThemeMode,
    type ThemeTokens,
} from './tokens';

interface ThemeContextValue {
    mode: ThemeMode;
    theme: ThemeTokens;
    setMode: (mode: ThemeMode) => void;
}

const ThemeContext = createContext<ThemeContextValue>({
    mode: defaultDarkTheme.mode,
    theme: defaultDarkTheme,
    setMode: () => undefined,
});

export const ThemeProvider = ({ children }: PropsWithChildren) => {
    const { colorScheme, themeParams, webApp } = useTelegram();
    const [mode, setMode] = useState<ThemeMode>(colorScheme ?? 'dark');

    useEffect(() => {
        if (colorScheme) {
            // eslint-disable-next-line react-hooks/set-state-in-effect
            setMode(colorScheme);
        }
    }, [colorScheme]);

    useEffect(() => {
        if (!webApp) {
            return;
        }

        const handleThemeChange = () => {
            setMode(webApp.colorScheme === 'light' ? 'light' : 'dark');
        };

        webApp.onEvent('themeChanged', handleThemeChange);
        return () => webApp.offEvent('themeChanged', handleThemeChange);
    }, [webApp]);

    const theme = useMemo(() => createTheme(mode, themeParams ?? undefined), [mode, themeParams]);

    useEffect(() => {
        applyTheme(theme);
    }, [theme]);

    return (
        <ThemeContext.Provider value={{ mode, theme, setMode }}>{children}</ThemeContext.Provider>
    );
};

// eslint-disable-next-line react-refresh/only-export-components
export const useTheme = () => useContext(ThemeContext);
