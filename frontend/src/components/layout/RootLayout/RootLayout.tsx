import { Outlet, useLocation, useMatches, useNavigate } from 'react-router-dom';
import { OnboardingGuard } from '../../../router/guards';
import type { AppRouteHandle } from '../../../router/types';
import { BottomNav, type BottomNavRoute } from '../BottomNav/BottomNav';
import styles from './RootLayout.module.css';

const resolveActiveRoute = (pathname: string): BottomNavRoute => {
    if (pathname.startsWith('/practice')) {
        return 'practice';
    }
    if (pathname.startsWith('/groups')) {
        return 'groups';
    }
    if (pathname.startsWith('/profile')) {
        return 'profile';
    }
    return 'home';
};

export const RootLayout = () => {
    const location = useLocation();
    const matches = useMatches();
    const navigate = useNavigate();

    const hideBottomNav = matches.some((match) => {
        const handle = match.handle as AppRouteHandle | undefined;
        return handle?.hideBottomNav;
    });

    const activeRoute = resolveActiveRoute(location.pathname);

    return (
        <OnboardingGuard>
            <div className={styles.shell}>
                <div className={styles.inner}>
                    <Outlet />
                </div>
                {!hideBottomNav && (
                    <BottomNav
                        activeRoute={activeRoute}
                        onNavigate={(path) => navigate(path)}
                        notificationCount={0}
                    />
                )}
            </div>
        </OnboardingGuard>
    );
};
