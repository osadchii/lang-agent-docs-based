import type { ReactNode } from 'react';
import { useEffect } from 'react';
import { createPortal } from 'react-dom';
import { classNames } from '../../../utils/classNames';
import { Button } from '../Button';
import styles from './Modal.module.css';

export type ModalType = 'alert' | 'bottomSheet' | 'fullScreen';

export interface ModalProps {
    open: boolean;
    onClose: () => void;
    title?: ReactNode;
    subtitle?: ReactNode;
    type?: ModalType;
    footer?: ReactNode;
    closeOnBackdrop?: boolean;
    hideCloseButton?: boolean;
    children: ReactNode;
}

export const Modal = ({
    open,
    onClose,
    title,
    subtitle,
    type = 'alert',
    footer,
    closeOnBackdrop = true,
    hideCloseButton = false,
    children,
}: ModalProps) => {
    useEffect(() => {
        if (!open) {
            return undefined;
        }

        const handleKeyDown = (event: KeyboardEvent) => {
            if (event.key === 'Escape') {
                onClose();
            }
        };

        const previousOverflow = document.body.style.overflow;
        document.body.style.overflow = 'hidden';
        window.addEventListener('keydown', handleKeyDown);

        return () => {
            document.body.style.overflow = previousOverflow;
            window.removeEventListener('keydown', handleKeyDown);
        };
    }, [open, onClose]);

    if (!open) {
        return null;
    }

    const handleBackdropClick = () => {
        if (closeOnBackdrop) {
            onClose();
        }
    };

    const dialogContent = (
        <div
            className={classNames(styles.overlay, type === 'bottomSheet' && styles.sheetOverlay)}
            role="presentation"
            onClick={handleBackdropClick}
        >
            <div
                role="dialog"
                aria-modal="true"
                aria-label={typeof title === 'string' ? title : undefined}
                className={classNames(
                    styles.dialog,
                    type === 'bottomSheet' && styles.bottomSheet,
                    type === 'fullScreen' && styles.fullscreen,
                )}
                onClick={(event) => event.stopPropagation()}
            >
                {type === 'bottomSheet' && <div className={styles.sheetHandle} />}
                {!hideCloseButton && (
                    <button type="button" className={styles.closeButton} onClick={onClose}>
                        ×
                    </button>
                )}
                {(title || subtitle) && (
                    <div className={styles.header}>
                        <div>
                            {title && <div className={styles.title}>{title}</div>}
                            {subtitle && <div className={styles.subtitle}>{subtitle}</div>}
                        </div>
                    </div>
                )}

                <div className={styles.content}>{children}</div>

                {footer && <div className={styles.footer}>{footer}</div>}
                {!footer && hideCloseButton && (
                    <div className={styles.footer}>
                        <Button variant="secondary" onClick={onClose}>
                            Закрыть
                        </Button>
                    </div>
                )}
            </div>
        </div>
    );

    return createPortal(dialogContent, document.body);
};
