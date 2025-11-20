import type { PropsWithChildren } from 'react';
import { createContext, useContext, useEffect, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import { classNames } from '../../../utils/classNames';
import styles from './Toast.module.css';

export type ToastType = 'success' | 'error' | 'warning' | 'info';

export interface ToastOptions {
    title?: string;
    description?: string;
    duration?: number;
    type?: ToastType;
}

interface ToastItem extends Required<ToastOptions> {
    id: string;
}

interface ToastContextValue {
    notify: (options: ToastOptions) => string;
    success: (title: string, description?: string) => string;
    error: (title: string, description?: string) => string;
    info: (title: string, description?: string) => string;
    warning: (title: string, description?: string) => string;
    dismiss: (id: string) => void;
}

const ToastContext = createContext<ToastContextValue | null>(null);

const DEFAULT_DURATION = 3200;

const ToastContainer = ({
    toasts,
    onClose,
}: {
    toasts: ToastItem[];
    onClose: (id: string) => void;
}) => {
    if (toasts.length === 0) {
        return null;
    }

    return createPortal(
        <div className={styles.container} role="status" aria-live="polite">
            {toasts.map((toast) => (
                <div
                    key={toast.id}
                    className={classNames(
                        styles.toast,
                        toast.type === 'success' && styles.typeSuccess,
                        toast.type === 'error' && styles.typeError,
                        toast.type === 'warning' && styles.typeWarning,
                        toast.type === 'info' && styles.typeInfo,
                    )}
                >
                    <div className={styles.accent} />
                    <div>
                        {toast.title && <div className={styles.title}>{toast.title}</div>}
                        {toast.description && (
                            <div className={styles.message}>{toast.description}</div>
                        )}
                    </div>
                    <button
                        type="button"
                        className={styles.close}
                        aria-label="Закрыть уведомление"
                        onClick={() => onClose(toast.id)}
                    >
                        ✕
                    </button>
                </div>
            ))}
        </div>,
        document.body,
    );
};

export const ToastProvider = ({ children }: PropsWithChildren) => {
    const [toasts, setToasts] = useState<ToastItem[]>([]);
    const timeouts = useRef<Record<string, number>>({});

    const dismiss = (id: string) => {
        setToasts((current) => current.filter((toast) => toast.id !== id));
        const timeout = timeouts.current[id];
        if (timeout) {
            window.clearTimeout(timeout);
            delete timeouts.current[id];
        }
    };

    useEffect(
        () => () => {
            Object.values(timeouts.current).forEach((timeout) => window.clearTimeout(timeout));
            timeouts.current = {};
        },
        [],
    );

    const notify = (options: ToastOptions): string => {
        const id = crypto.randomUUID();
        const toast: ToastItem = {
            id,
            title: options.title ?? 'Готово',
            description: options.description ?? '',
            type: options.type ?? 'info',
            duration: options.duration ?? DEFAULT_DURATION,
        };

        setToasts((current) => [...current, toast]);
        timeouts.current[id] = window.setTimeout(() => {
            dismiss(id);
        }, toast.duration);

        return id;
    };

    const success = (title: string, description?: string) =>
        notify({ title, description, type: 'success' });
    const error = (title: string, description?: string) =>
        notify({ title, description, type: 'error', duration: 4200 });
    const info = (title: string, description?: string) =>
        notify({ title, description, type: 'info' });
    const warning = (title: string, description?: string) =>
        notify({ title, description, type: 'warning' });

    return (
        <ToastContext.Provider value={{ notify, success, error, info, warning, dismiss }}>
            {children}
            <ToastContainer toasts={toasts} onClose={dismiss} />
        </ToastContext.Provider>
    );
};

// eslint-disable-next-line react-refresh/only-export-components
export const useToast = () => {
    const context = useContext(ToastContext);
    if (!context) {
        throw new Error('useToast must be used within ToastProvider');
    }
    return context;
};
