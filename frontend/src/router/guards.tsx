import { type PropsWithChildren, useEffect } from 'react';
import { Navigate, Outlet, useLocation, useNavigate } from 'react-router-dom';
import { useAuthContext } from '../providers/AuthProvider';
import { useOnboarding } from '../providers/OnboardingProvider';
import { classNames } from '../utils/classNames';
import styles from './Guards.module.css';

interface GuardStateProps {
    title: string;
    description?: string;
    actionLabel?: string;
    onAction?: () => void;
}

const GuardState = ({ title, description, actionLabel, onAction }: GuardStateProps) => (
    <div className={styles.guardState}>
        <div className={styles.spinner} />
        <div>
            <div className={styles.title}>{title}</div>
            {description && <div className={styles.subtitle}>{description}</div>}
        </div>
        {actionLabel && onAction && (
            <button type="button" className={styles.retryButton} onClick={onAction}>
                {actionLabel}
            </button>
        )}
    </div>
);

export const AuthGuard = () => {
    const { telegramReady, status, error } = useAuthContext();

    if (!telegramReady) {
        return (
            <GuardState
                title="Инициализируем Telegram WebApp"
                description="Синхронизируем тему и кнопки для Mini App"
            />
        );
    }

    if (status === 'idle' || status === 'loading') {
        return <GuardState title="Проверяем доступ" description="Авторизация через initData..." />;
    }

    if (status === 'error') {
        return (
            <div className={classNames(styles.guardState, styles.error)}>
                <div>
                    <div className={styles.title}>Не получилось авторизоваться</div>
                    <div className={styles.subtitle}>
                        {error ?? 'Откройте приложение из Telegram, чтобы продолжить.'}
                    </div>
                </div>
                <button
                    type="button"
                    className={styles.retryButton}
                    onClick={() => window.location.reload()}
                >
                    Попробовать снова
                </button>
            </div>
        );
    }

    return <Outlet />;
};

export const OnboardingGuard = ({ children }: PropsWithChildren) => {
    const { completed, checking } = useOnboarding();
    const location = useLocation();
    const navigate = useNavigate();

    useEffect(() => {
        if (!checking && !completed && !location.pathname.startsWith('/onboarding')) {
            navigate('/onboarding', { replace: true, state: { from: location.pathname } });
        }
    }, [checking, completed, location.pathname, navigate]);

    if (checking) {
        return (
            <GuardState
                title="Проверяем профиль"
                description="Синхронизируем прогресс и настройки"
            />
        );
    }

    if (!completed && !location.pathname.startsWith('/onboarding')) {
        return null;
    }

    if (children) {
        return <>{children}</>;
    }

    return <Outlet />;
};

export const OnboardingCompletedRedirect = ({ children }: PropsWithChildren) => {
    const { completed, checking } = useOnboarding();

    if (checking) {
        return (
            <GuardState
                title="Проверяем профиль"
                description="Синхронизируем прогресс и настройки"
            />
        );
    }

    if (completed) {
        return <Navigate to="/" replace />;
    }

    if (children) {
        return <>{children}</>;
    }

    return <Outlet />;
};
