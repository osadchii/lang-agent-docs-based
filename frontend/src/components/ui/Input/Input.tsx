import type { InputHTMLAttributes, ReactNode } from 'react';
import { forwardRef } from 'react';
import { classNames } from '../../../utils/classNames';
import styles from './Input.module.css';

export interface InputProps extends Omit<InputHTMLAttributes<HTMLInputElement>, 'size'> {
    label?: string;
    hint?: string;
    error?: string;
    optional?: boolean;
    leftIcon?: ReactNode;
    rightIcon?: ReactNode;
}

export const Input = forwardRef<HTMLInputElement, InputProps>(function Input(
    { label, hint, error, optional, leftIcon, rightIcon, className, disabled, ...rest },
    forwardedRef,
) {
    return (
        <label className={classNames(styles.field, className)}>
            {(label || optional) && (
                <div className={styles.labelRow}>
                    {label && <span className={styles.label}>{label}</span>}
                    {optional && <span className={styles.optional}>Optional</span>}
                </div>
            )}

            <div
                className={classNames(
                    styles.control,
                    error && styles.error,
                    disabled && styles.disabled,
                )}
            >
                {leftIcon && <span className={styles.icon}>{leftIcon}</span>}
                <input
                    ref={forwardedRef}
                    className={styles.input}
                    disabled={disabled}
                    aria-invalid={Boolean(error)}
                    aria-describedby={error ? `${rest.id}-error` : undefined}
                    {...rest}
                />
                {rightIcon && <span className={styles.icon}>{rightIcon}</span>}
            </div>

            {error ? (
                <span className={styles.errorText} id={rest.id ? `${rest.id}-error` : undefined}>
                    {error}
                </span>
            ) : (
                hint && <span className={styles.hint}>{hint}</span>
            )}
        </label>
    );
});
