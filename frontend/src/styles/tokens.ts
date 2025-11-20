import type { ThemeParams } from '../types/telegram';

export type ThemeMode = 'light' | 'dark';

export interface ThemeColors {
    background: {
        primary: string;
        secondary: string;
        surface: string;
        elevated: string;
        overlay: string;
    };
    text: {
        primary: string;
        secondary: string;
        muted: string;
        inverted: string;
    };
    accent: {
        primary: string;
        secondary: string;
        highlight: string;
        link: string;
    };
    status: {
        success: string;
        warning: string;
        danger: string;
        info: string;
    };
    border: {
        subtle: string;
        strong: string;
    };
}

export interface ThemeGradients {
    accent: string;
    surface: string;
    soft: string;
}

export interface ThemeShadows {
    soft: string;
    medium: string;
    hard: string;
}

export interface ThemeRadii {
    xs: string;
    sm: string;
    md: string;
    lg: string;
    xl: string;
    pill: string;
}

export interface ThemeTypography {
    fontFamily: string;
    monospaceFamily: string;
    headingWeight: number;
    bodyWeight: number;
}

export interface ThemeTokens {
    mode: ThemeMode;
    colors: ThemeColors;
    gradients: ThemeGradients;
    shadows: ThemeShadows;
    radii: ThemeRadii;
    typography: ThemeTypography;
}

const basePalettes: Record<ThemeMode, ThemeTokens> = {
    dark: {
        mode: 'dark',
        colors: {
            background: {
                primary: '#090f27',
                secondary: '#0e1634',
                surface: '#111a3d',
                elevated: '#192355',
                overlay: 'rgba(2, 6, 23, 0.7)',
            },
            text: {
                primary: '#f7f8ff',
                secondary: '#c8cee6',
                muted: '#9fa6c5',
                inverted: '#050915',
            },
            accent: {
                primary: '#ff7a3c',
                secondary: '#ff5e78',
                highlight: '#8d8bff',
                link: '#5ac8ff',
            },
            status: {
                success: '#3fd6a5',
                warning: '#f5c56a',
                danger: '#ff7b70',
                info: '#5ac8ff',
            },
            border: {
                subtle: '#242d52',
                strong: '#2f3a63',
            },
        },
        gradients: {
            accent: 'linear-gradient(120deg, #ff7a3c, #ff3f6e 45%, #8d8bff 100%)',
            surface: 'linear-gradient(145deg, rgba(255,255,255,0.06), rgba(255,255,255,0))',
            soft: 'linear-gradient(180deg, rgba(255, 126, 94, 0.12), rgba(141, 139, 255, 0.08))',
        },
        shadows: {
            soft: '0 14px 45px rgba(0, 0, 0, 0.35)',
            medium: '0 10px 30px rgba(11, 14, 38, 0.5)',
            hard: '0 20px 50px rgba(0, 0, 0, 0.55)',
        },
        radii: {
            xs: '6px',
            sm: '10px',
            md: '14px',
            lg: '18px',
            xl: '24px',
            pill: '999px',
        },
        typography: {
            fontFamily:
                '"Space Grotesk", "Manrope", "Inter", -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif',
            monospaceFamily:
                '"JetBrains Mono", "SFMono-Regular", Consolas, "Liberation Mono", monospace',
            headingWeight: 700,
            bodyWeight: 500,
        },
    },
    light: {
        mode: 'light',
        colors: {
            background: {
                primary: '#f7f8ff',
                secondary: '#eef1ff',
                surface: '#e2e6ff',
                elevated: '#ffffff',
                overlay: 'rgba(12, 23, 42, 0.45)',
            },
            text: {
                primary: '#0c1224',
                secondary: '#2f3654',
                muted: '#4b556b',
                inverted: '#ffffff',
            },
            accent: {
                primary: '#ff6b3d',
                secondary: '#ff3f6e',
                highlight: '#6658e8',
                link: '#0f9cf3',
            },
            status: {
                success: '#1f9d67',
                warning: '#c97a19',
                danger: '#e15252',
                info: '#0f9cf3',
            },
            border: {
                subtle: '#d6ddf6',
                strong: '#b4c0ec',
            },
        },
        gradients: {
            accent: 'linear-gradient(115deg, #ff8558, #ff3e73 55%, #6658e8 100%)',
            surface: 'linear-gradient(145deg, rgba(255,255,255,0.75), rgba(255,255,255,0.95))',
            soft: 'linear-gradient(180deg, rgba(255, 126, 94, 0.14), rgba(102, 88, 232, 0.07))',
        },
        shadows: {
            soft: '0 12px 26px rgba(15, 23, 42, 0.14)',
            medium: '0 16px 34px rgba(11, 20, 38, 0.18)',
            hard: '0 20px 55px rgba(15, 23, 42, 0.22)',
        },
        radii: {
            xs: '6px',
            sm: '10px',
            md: '14px',
            lg: '18px',
            xl: '24px',
            pill: '999px',
        },
        typography: {
            fontFamily:
                '"Space Grotesk", "Manrope", "Inter", -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif',
            monospaceFamily:
                '"JetBrains Mono", "SFMono-Regular", Consolas, "Liberation Mono", monospace',
            headingWeight: 700,
            bodyWeight: 500,
        },
    },
};

const normalizeColor = (value?: string, fallback?: string): string => {
    if (!value) {
        return fallback ?? '';
    }

    if (value.startsWith('#')) {
        return value;
    }

    return fallback ?? '#ffffff';
};

const mergeWithTelegram = (mode: ThemeMode, themeParams?: ThemeParams): ThemeTokens => {
    const base = basePalettes[mode];

    if (!themeParams) {
        return base;
    }

    return {
        ...base,
        colors: {
            ...base.colors,
            background: {
                ...base.colors.background,
                primary: normalizeColor(themeParams.bg_color, base.colors.background.primary),
                secondary: normalizeColor(
                    themeParams.secondary_bg_color,
                    base.colors.background.secondary,
                ),
            },
            text: {
                ...base.colors.text,
                primary: normalizeColor(themeParams.text_color, base.colors.text.primary),
                muted: normalizeColor(themeParams.hint_color, base.colors.text.muted),
                secondary: normalizeColor(themeParams.text_color, base.colors.text.secondary),
            },
            accent: {
                ...base.colors.accent,
                primary: normalizeColor(themeParams.button_color, base.colors.accent.primary),
                link: normalizeColor(themeParams.link_color, base.colors.accent.link),
            },
        },
    };
};

export const createTheme = (mode: ThemeMode, themeParams?: ThemeParams): ThemeTokens =>
    mergeWithTelegram(mode, themeParams);

export const applyTheme = (theme: ThemeTokens): void => {
    const root = document.documentElement;

    root.style.setProperty('color-scheme', theme.mode);
    root.style.setProperty('--color-bg-primary', theme.colors.background.primary);
    root.style.setProperty('--color-bg-secondary', theme.colors.background.secondary);
    root.style.setProperty('--color-surface', theme.colors.background.surface);
    root.style.setProperty('--color-elevated', theme.colors.background.elevated);
    root.style.setProperty('--color-overlay', theme.colors.background.overlay);

    root.style.setProperty('--color-text-primary', theme.colors.text.primary);
    root.style.setProperty('--color-text-secondary', theme.colors.text.secondary);
    root.style.setProperty('--color-text-muted', theme.colors.text.muted);
    root.style.setProperty('--color-text-inverted', theme.colors.text.inverted);

    root.style.setProperty('--color-accent', theme.colors.accent.primary);
    root.style.setProperty('--color-accent-strong', theme.colors.accent.secondary);
    root.style.setProperty('--color-accent-highlight', theme.colors.accent.highlight);
    root.style.setProperty('--color-link', theme.colors.accent.link);

    root.style.setProperty('--color-success', theme.colors.status.success);
    root.style.setProperty('--color-warning', theme.colors.status.warning);
    root.style.setProperty('--color-danger', theme.colors.status.danger);
    root.style.setProperty('--color-info', theme.colors.status.info);

    root.style.setProperty('--color-border-subtle', theme.colors.border.subtle);
    root.style.setProperty('--color-border-strong', theme.colors.border.strong);

    root.style.setProperty('--gradient-accent', theme.gradients.accent);
    root.style.setProperty('--gradient-surface', theme.gradients.surface);
    root.style.setProperty('--gradient-soft', theme.gradients.soft);

    root.style.setProperty('--shadow-soft', theme.shadows.soft);
    root.style.setProperty('--shadow-medium', theme.shadows.medium);
    root.style.setProperty('--shadow-hard', theme.shadows.hard);

    root.style.setProperty('--radius-xs', theme.radii.xs);
    root.style.setProperty('--radius-sm', theme.radii.sm);
    root.style.setProperty('--radius-md', theme.radii.md);
    root.style.setProperty('--radius-lg', theme.radii.lg);
    root.style.setProperty('--radius-xl', theme.radii.xl);
    root.style.setProperty('--radius-pill', theme.radii.pill);

    root.style.setProperty('--font-sans', theme.typography.fontFamily);
    root.style.setProperty('--font-mono', theme.typography.monospaceFamily);
    root.style.setProperty('--font-weight-heading', theme.typography.headingWeight.toString());
    root.style.setProperty('--font-weight-body', theme.typography.bodyWeight.toString());
};

export const defaultDarkTheme = basePalettes.dark;
export const defaultLightTheme = basePalettes.light;
