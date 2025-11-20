import type { HTMLAttributes, ReactNode } from 'react';
import { classNames } from '../../../utils/classNames';
import styles from './Badge.module.css';

type BadgeVariant = 'default' | 'success' | 'error' | 'warning' | 'info';
type BadgeSize = 'sm' | 'md';

export interface BadgeProps extends HTMLAttributes<HTMLSpanElement> {
    variant?: BadgeVariant;
    size?: BadgeSize;
    icon?: ReactNode;
}

export const Badge = ({
    children,
    className,
    variant = 'default',
    size = 'sm',
    icon,
    ...rest
}: BadgeProps) => (
    <span
        className={classNames(
            styles.badge,
            styles[`variant${variant[0].toUpperCase()}${variant.slice(1)}`],
            size === 'md' && styles.sizeMd,
            className,
        )}
        {...rest}
    >
        {icon}
        {children}
    </span>
);
