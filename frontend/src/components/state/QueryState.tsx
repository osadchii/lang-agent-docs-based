import { type ReactNode } from 'react';
import { classNames } from '../../utils/classNames';
import styles from './QueryState.module.css';

type Variant = 'loading' | 'error' | 'empty';

interface QueryStateProps {
    variant?: Variant;
    title: string;
    description?: string | ReactNode;
    actionLabel?: string;
    onAction?: () => void;
}

export const QueryState = ({
    variant = 'loading',
    title,
    description,
    actionLabel,
    onAction,
}: QueryStateProps) => {
    const renderIcon = () => {
        if (variant === 'loading') {
            return <span className={styles.spinner} aria-hidden="true" />;
        }
        if (variant === 'error') {
            return (
                <span className={styles.icon} role="img" aria-label="Ошибка">
                    ⚠️
                </span>
            );
        }
        return (
            <span className={styles.icon} role="img" aria-label="Пусто">
                💬
            </span>
        );
    };

    return (
        <div
            className={classNames(
                styles.container,
                variant === 'error' && styles.error,
                variant === 'empty' && styles.empty,
            )}
        >
            {renderIcon()}
            <div className={styles.textBlock}>
                <div className={styles.title}>{title}</div>
                {description && <div className={styles.description}>{description}</div>}
            </div>
            {actionLabel && onAction && (
                <button type="button" className={styles.action} onClick={onAction}>
                    {actionLabel}
                </button>
            )}
        </div>
    );
};
