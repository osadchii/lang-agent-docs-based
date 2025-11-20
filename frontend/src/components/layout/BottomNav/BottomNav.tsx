import type { ReactNode } from 'react';
import { useCallback } from 'react';
import { useHapticFeedback } from '../../../hooks/useHapticFeedback';
import { classNames } from '../../../utils/classNames';
import styles from './BottomNav.module.css';

export type BottomNavRoute = 'home' | 'practice' | 'groups' | 'profile';

interface BottomNavProps {
    activeRoute: BottomNavRoute;
    notificationCount?: number;
    onNavigate: (path: string) => void;
}

interface NavItem {
    id: BottomNavRoute;
    label: string;
    path: string;
    icon: ReactNode;
    badge?: number;
}

const icons: Record<BottomNavRoute, ReactNode> = {
    home: (
        <svg viewBox="0 0 24 24" role="presentation">
            <path
                d="M4 10.5 12 4l8 6.5V19a1 1 0 0 1-1 1h-4.5v-5h-5v5H5a1 1 0 0 1-1-1z"
                fill="currentColor"
            />
        </svg>
    ),
    practice: (
        <svg viewBox="0 0 24 24" role="presentation">
            <path
                d="M6 5h12v3H6zm0 6h12v3H6zm0 6h7v2H6z"
                fill="currentColor"
                fillRule="evenodd"
                clipRule="evenodd"
            />
        </svg>
    ),
    groups: (
        <svg viewBox="0 0 24 24" role="presentation">
            <path
                d="M8.5 7a3.5 3.5 0 1 1 7 0 3.5 3.5 0 0 1-7 0Zm-3 10a4.5 4.5 0 0 1 9 0v1H5.5zm10 .5a3.5 3.5 0 0 1 4.55-3.33A4.5 4.5 0 0 0 14 17v1h1.5zM17 6a3 3 0 0 0-2.11.89A4.48 4.48 0 0 1 16.5 9 4.47 4.47 0 0 1 15 12.1V13a3 3 0 1 0 2-7Z"
                fill="currentColor"
            />
        </svg>
    ),
    profile: (
        <svg viewBox="0 0 24 24" role="presentation">
            <path
                d="M12 4a4 4 0 1 1 0 8 4 4 0 0 1 0-8Zm0 10c3.866 0 7 2.239 7 5v1H5v-1c0-2.761 3.134-5 7-5Z"
                fill="currentColor"
            />
        </svg>
    ),
};

export const BottomNav = ({ activeRoute, notificationCount = 0, onNavigate }: BottomNavProps) => {
    const { selectionChanged } = useHapticFeedback();

    const navItems: NavItem[] = [
        { id: 'home', label: 'Главная', path: '/', icon: icons.home },
        { id: 'practice', label: 'Практика', path: '/practice/cards', icon: icons.practice },
        {
            id: 'groups',
            label: 'Группы',
            path: '/groups',
            icon: icons.groups,
            badge: notificationCount,
        },
        { id: 'profile', label: 'Профиль', path: '/profile', icon: icons.profile },
    ];

    const handleNavigate = useCallback(
        (path: string) => {
            selectionChanged();
            onNavigate(path);
        },
        [onNavigate, selectionChanged],
    );

    return (
        <nav className={styles.nav} aria-label="Основная навигация">
            <div className={styles.inner}>
                {navItems.map((item) => {
                    const isActive = item.id === activeRoute;
                    const badge = item.badge ?? 0;
                    return (
                        <button
                            key={item.id}
                            type="button"
                            aria-current={isActive ? 'page' : undefined}
                            className={classNames(styles.item, isActive && styles.active)}
                            onClick={() => handleNavigate(item.path)}
                        >
                            <span className={styles.icon} aria-hidden>
                                {item.icon}
                                {badge > 0 && <span className={styles.badge}>{badge}</span>}
                            </span>
                            <span className={styles.label}>{item.label}</span>
                        </button>
                    );
                })}
            </div>
        </nav>
    );
};
