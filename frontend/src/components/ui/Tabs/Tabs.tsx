import type { ReactNode } from 'react';
import { classNames } from '../../../utils/classNames';
import styles from './Tabs.module.css';

export interface TabItem {
    id: string;
    label: ReactNode;
    icon?: ReactNode;
}

export interface TabsProps {
    tabs: TabItem[];
    activeTab: string;
    onChange: (tabId: string) => void;
    className?: string;
}

export const Tabs = ({ tabs, activeTab, onChange, className }: TabsProps) => {
    return (
        <div className={classNames(styles.tabs, className)}>
            <div className={styles.list} role="tablist">
                {tabs.map((tab) => {
                    const isActive = tab.id === activeTab;
                    return (
                        <button
                            key={tab.id}
                            type="button"
                            className={classNames(styles.tab, isActive && styles.active)}
                            onClick={() => onChange(tab.id)}
                            role="tab"
                            aria-selected={isActive}
                        >
                            {tab.icon && <span className={styles.icon}>{tab.icon}</span>}
                            <span>{tab.label}</span>
                        </button>
                    );
                })}
            </div>
        </div>
    );
};
