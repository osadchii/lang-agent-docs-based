import type { ReactNode } from 'react';
import { useHapticFeedback } from '../../../hooks/useHapticFeedback';
import { classNames } from '../../../utils/classNames';
import styles from './TabBar.module.css';

export interface TabBarItem {
    id: string;
    label: string;
    icon?: ReactNode;
}

interface TabBarProps {
    tabs: TabBarItem[];
    activeTab: string;
    onChange: (tabId: string) => void;
}

export const TabBar = ({ tabs, activeTab, onChange }: TabBarProps) => {
    const { selectionChanged } = useHapticFeedback();

    return (
        <div className={styles.tabBar} role="tablist">
            {tabs.map((tab) => {
                const isActive = tab.id === activeTab;
                return (
                    <button
                        key={tab.id}
                        type="button"
                        role="tab"
                        aria-selected={isActive}
                        className={classNames(styles.tab, isActive && styles.active)}
                        onClick={() => {
                            selectionChanged();
                            onChange(tab.id);
                        }}
                    >
                        {tab.icon && <span className={styles.icon}>{tab.icon}</span>}
                        <span>{tab.label}</span>
                    </button>
                );
            })}
        </div>
    );
};
