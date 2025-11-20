import type { HTMLAttributes, ReactNode } from 'react';
import { classNames } from '../../../utils/classNames';
import styles from './Progress.module.css';

type ProgressType = 'linear' | 'spinner';

export interface ProgressProps extends HTMLAttributes<HTMLDivElement> {
    value?: number;
    label?: ReactNode;
    type?: ProgressType;
    indeterminate?: boolean;
    showValue?: boolean;
}

export const Progress = ({
    value = 0,
    label,
    type = 'linear',
    indeterminate = false,
    showValue = false,
    className,
    ...rest
}: ProgressProps) => {
    if (type === 'spinner') {
        return (
            <div className={classNames(styles.wrapper, className)} {...rest}>
                {label && <div className={styles.labelRow}>{label}</div>}
                <div className={styles.spinner} aria-label="Загрузка" role="status" />
            </div>
        );
    }

    const normalized = Math.min(100, Math.max(0, value));

    return (
        <div className={classNames(styles.wrapper, className)} {...rest}>
            {(label || showValue) && (
                <div className={styles.labelRow}>
                    {label && <span>{label}</span>}
                    {showValue && <span>{normalized}%</span>}
                </div>
            )}
            <div
                className={styles.bar}
                role="progressbar"
                aria-valuenow={normalized}
                aria-valuemin={0}
                aria-valuemax={100}
            >
                <div
                    className={classNames(styles.value, indeterminate && styles.indeterminate)}
                    style={{ width: indeterminate ? undefined : `${normalized}%` }}
                />
            </div>
        </div>
    );
};
