import type { HTMLAttributes, ReactNode } from 'react';
import { classNames } from '../../../utils/classNames';
import styles from './Card.module.css';

type CardPadding = 'none' | 'sm' | 'md' | 'lg';

export interface CardProps extends Omit<HTMLAttributes<HTMLDivElement>, 'title'> {
    padding?: CardPadding;
    interactive?: boolean;
    elevated?: boolean;
    gradient?: boolean;
    title?: ReactNode;
    subtitle?: ReactNode;
    footer?: ReactNode;
}

const paddingClassName: Record<CardPadding, string> = {
    none: styles.paddingNone,
    sm: styles.paddingSm,
    md: '',
    lg: styles.paddingLg,
};

export const Card = ({
    children,
    className,
    padding = 'md',
    interactive = false,
    elevated = false,
    gradient = false,
    title,
    subtitle,
    footer,
    ...rest
}: CardProps) => (
    <div
        className={classNames(
            styles.card,
            interactive && styles.interactive,
            elevated && styles.elevated,
            gradient && styles.gradient,
            paddingClassName[padding],
            className,
        )}
        {...rest}
    >
        {(title || subtitle) && (
            <div className={styles.header}>
                {title && <div className={styles.title}>{title}</div>}
                {subtitle && <div className={styles.subtitle}>{subtitle}</div>}
            </div>
        )}

        {children}

        {footer && <div className={styles.footer}>{footer}</div>}
    </div>
);
