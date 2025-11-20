import { Component, type ErrorInfo, type ReactNode } from 'react';
import styles from './AppErrorBoundary.module.css';

interface Props {
    children: ReactNode;
}

interface State {
    hasError: boolean;
    error: Error | null;
}

export class AppErrorBoundary extends Component<Props, State> {
    state: State = {
        hasError: false,
        error: null,
    };

    static getDerivedStateFromError(error: Error): State {
        return { hasError: true, error };
    }

    componentDidCatch(error: Error, info: ErrorInfo) {
        console.error('Unhandled application error', error, info);
    }

    handleReload = () => {
        window.location.reload();
    };

    render() {
        if (this.state.hasError) {
            return (
                <div className={styles.wrapper}>
                    <div className={styles.card}>
                        <div className={styles.badge}>Сбой приложения</div>
                        <h1 className={styles.title}>Что-то пошло не так</h1>
                        <p className={styles.description}>
                            Мы уже записали ошибку в консоль. Попробуйте перезагрузить приложение
                            или открыть его заново из Telegram.
                        </p>
                        {this.state.error?.message && (
                            <code className={styles.errorText}>{this.state.error.message}</code>
                        )}
                        <button
                            type="button"
                            className={styles.reloadButton}
                            onClick={this.handleReload}
                        >
                            Перезагрузить
                        </button>
                    </div>
                </div>
            );
        }

        return this.props.children;
    }
}
