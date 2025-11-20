import type { ReactNode } from 'react';
import { useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { useHapticFeedback } from '../../../hooks/useHapticFeedback';
import { classNames } from '../../../utils/classNames';
import styles from './Header.module.css';

interface HeaderProps {
    title?: string;
    subtitle?: string;
    showBack?: boolean;
    onBack?: () => void;
    actions?: ReactNode;
    dense?: boolean;
}

export const Header = ({
    title,
    subtitle,
    showBack = false,
    onBack,
    actions,
    dense = false,
}: HeaderProps) => {
    const navigate = useNavigate();
    const { impact } = useHapticFeedback();

    const handleBack = useCallback(() => {
        impact('light');
        if (onBack) {
            onBack();
            return;
        }
        navigate(-1);
    }, [impact, navigate, onBack]);

    return (
        <header className={classNames(styles.header, dense && styles.dense)}>
            <div className={styles.left}>
                {showBack && (
                    <button
                        type="button"
                        className={styles.back}
                        onClick={handleBack}
                        aria-label="Назад"
                    >
                        <span aria-hidden>←</span>
                    </button>
                )}
                <div>
                    {title && <div className={styles.title}>{title}</div>}
                    {subtitle && <div className={styles.subtitle}>{subtitle}</div>}
                </div>
            </div>
            {actions && <div className={styles.actions}>{actions}</div>}
        </header>
    );
};
