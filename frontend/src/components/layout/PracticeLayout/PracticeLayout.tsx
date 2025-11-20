import type { PropsWithChildren } from 'react';
import { Outlet, useLocation, useNavigate } from 'react-router-dom';
import { Header } from '../Header/Header';
import { TabBar, type TabBarItem } from '../TabBar/TabBar';
import { classNames } from '../../../utils/classNames';
import styles from './PracticeLayout.module.css';

interface PracticeLayoutProps extends PropsWithChildren {
    title: string;
    subtitle?: string;
    backTo?: string;
    tabs?: TabBarItem[];
    activeTab?: string;
    onTabChange?: (tabId: string) => void;
    fullHeight?: boolean;
}

export const PracticeLayout = ({
    title,
    subtitle,
    backTo,
    tabs,
    activeTab,
    onTabChange,
    fullHeight = false,
    children,
}: PracticeLayoutProps) => {
    const navigate = useNavigate();
    const location = useLocation();

    const derivedActiveTab =
        activeTab ?? (location.pathname.includes('exercises') ? 'exercises' : 'cards');
    const changeTab =
        onTabChange ??
        ((tabId: string) =>
            navigate(tabId === 'cards' ? '/practice/cards' : '/practice/exercises'));

    return (
        <div className={classNames(styles.layout, fullHeight && styles.fullHeight)}>
            <Header
                title={title}
                subtitle={subtitle}
                showBack={Boolean(backTo)}
                onBack={backTo ? () => navigate(backTo) : undefined}
                dense
            />

            {tabs && tabs.length > 0 && (
                <TabBar tabs={tabs} activeTab={derivedActiveTab} onChange={changeTab} />
            )}

            <div className={styles.body}>{children ?? <Outlet />}</div>
        </div>
    );
};
