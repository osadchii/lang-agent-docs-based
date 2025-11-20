import type { ButtonHTMLAttributes, ReactNode } from 'react';
import { forwardRef } from 'react';
import { classNames } from '../../../utils/classNames';
import styles from './Button.module.css';

type ButtonVariant = 'primary' | 'secondary' | 'ghost' | 'mono' | 'danger';
type ButtonSize = 'sm' | 'md' | 'lg';

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
    variant?: ButtonVariant;
    size?: ButtonSize;
    fullWidth?: boolean;
    loading?: boolean;
    icon?: ReactNode;
    iconPosition?: 'left' | 'right';
}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
    function Button(props, forwardedRef) {
        const {
            children,
            className,
            variant = 'primary',
            size = 'md',
            fullWidth = false,
            loading = false,
            disabled = false,
            icon,
            iconPosition = 'left',
            type = 'button',
            ...rest
        } = props;

        const isIconOnly = Boolean(icon && !children);
        const isDisabled = disabled || loading;

        return (
            <button
                ref={forwardedRef}
                className={classNames(
                    styles.button,
                    styles[`variant${variant[0].toUpperCase()}${variant.slice(1)}`],
                    size === 'sm' && styles.sizeSm,
                    size === 'lg' && styles.sizeLg,
                    fullWidth && styles.fullWidth,
                    isDisabled && styles.disabled,
                    loading && styles.loading,
                    isIconOnly && styles.iconOnly,
                    className,
                )}
                disabled={isDisabled}
                type={type}
                aria-busy={loading}
                {...rest}
            >
                <span className={styles.content}>
                    {icon && iconPosition === 'left' && <span className={styles.icon}>{icon}</span>}
                    {children}
                    {icon && iconPosition === 'right' && (
                        <span className={styles.icon}>{icon}</span>
                    )}
                    {loading && <span className={styles.spinner} aria-hidden />}
                </span>
            </button>
        );
    },
);
