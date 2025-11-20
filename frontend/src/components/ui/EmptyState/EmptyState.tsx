import type { ReactNode } from 'react';
import { classNames } from '../../../utils/classNames';
import styles from './EmptyState.module.css';

export interface EmptyStateProps {
    icon?: ReactNode;
    title: string;
    description: string;
    actions?: ReactNode;
    className?: string;
}

export const EmptyState = ({ icon, title, description, actions, className }: EmptyStateProps) => (
    <div className={classNames(styles.emptyState, className)}>
        {icon && <div className={styles.icon}>{icon}</div>}
        <div className={styles.title}>{title}</div>
        <div className={styles.description}>{description}</div>
        {actions && <div className={styles.actions}>{actions}</div>}
    </div>
);
