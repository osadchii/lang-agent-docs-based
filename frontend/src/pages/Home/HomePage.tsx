import { type FormEvent, useCallback, useEffect, useMemo, useState } from 'react';
import { fetchChatHistory, sendChatMessage } from '../../api/chat';
import { useAuth } from '../../hooks/useAuth';
import { useTelegram } from '../../hooks/useTelegram';
import type { ChatMessage, PaginationMeta } from '../../types/api';
import './HomePage.css';

const PAGE_SIZE = 20;

export const HomePage = () => {
    const { user: telegramUser, platform, colorScheme, isReady, initData } = useTelegram();
    const { user, status: authStatus, error: authError } = useAuth(initData);

    const [messages, setMessages] = useState<ChatMessage[]>([]);
    const [pagination, setPagination] = useState<PaginationMeta | null>(null);
    const [profileId, setProfileId] = useState<string | undefined>(undefined);
    const [messageText, setMessageText] = useState('');
    const [historyError, setHistoryError] = useState<string | null>(null);
    const [formError, setFormError] = useState<string | null>(null);
    const [isLoadingHistory, setIsLoadingHistory] = useState(false);
    const [isSending, setIsSending] = useState(false);

    const username = user?.first_name ?? telegramUser?.first_name ?? 'друг';
    const isAuthReady = authStatus === 'success';
    const isInitialLoading = !isReady || authStatus === 'idle' || authStatus === 'loading';

    const loadHistory = useCallback(
        async (options?: { offset?: number; append?: boolean }) => {
            if (!isAuthReady) {
                return;
            }

            const offset = options?.offset ?? 0;
            const append = options?.append ?? false;

            setIsLoadingHistory(true);
            setHistoryError(null);

            try {
                const response = await fetchChatHistory({
                    profileId,
                    limit: PAGE_SIZE,
                    offset,
                });

                const detectedProfile = response.messages.at(-1)?.profile_id;
                if (!profileId && detectedProfile) {
                    setProfileId(detectedProfile);
                }

                setMessages((prev) =>
                    append ? [...response.messages, ...prev] : response.messages,
                );
                setPagination(response.pagination);
            } catch (error) {
                console.error('Failed to load history', error);
                setHistoryError('Не удалось загрузить историю диалога.');
            } finally {
                setIsLoadingHistory(false);
            }
        },
        [isAuthReady, profileId],
    );

    useEffect(() => {
        if (isAuthReady) {
            loadHistory({ offset: 0, append: false }).catch(() => null);
        }
    }, [isAuthReady, loadHistory]);

    const handleLoadOlder = useCallback(() => {
        if (!pagination?.has_more || pagination.next_offset == null) {
            return;
        }
        loadHistory({ offset: pagination.next_offset, append: true }).catch(() => null);
    }, [pagination, loadHistory]);

    const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
        event.preventDefault();
        if (!messageText.trim() || !isAuthReady) {
            return;
        }

        setIsSending(true);
        setFormError(null);

        try {
            const response = await sendChatMessage({
                message: messageText.trim(),
                profile_id: profileId,
            });

            if (!profileId) {
                setProfileId(response.profile_id);
            }

            setMessageText('');
            await loadHistory({ offset: 0, append: false });
        } catch (error) {
            console.error('Failed to send message', error);
            setFormError('Не удалось отправить сообщение. Попробуйте ещё раз.');
        } finally {
            setIsSending(false);
        }
    };

    const formattedMessages = useMemo(() => {
        const formatter = new Intl.DateTimeFormat('ru-RU', {
            hour: '2-digit',
            minute: '2-digit',
        });

        return messages.map((message) => ({
            ...message,
            formattedTime: formatter.format(new Date(message.timestamp)),
        }));
    }, [messages]);

    if (isInitialLoading) {
        return (
            <div className="home-page loading">
                <div className="loader" />
                <p>Подготавливаем Mini App...</p>
            </div>
        );
    }

    if (authStatus === 'error') {
        return (
            <div className="home-page error-state">
                <h2>Не удалось авторизоваться 😔</h2>
                <p>{authError}</p>
                <p className="hint">
                    Убедитесь, что Mini App открыта внутри Telegram и попробуйте перезапустить
                    приложение.
                </p>
            </div>
        );
    }

    return (
        <div className="home-page">
            <header className="home-header">
                <div>
                    <p className="eyebrow">Lang Agent</p>
                    <h1 className="title">Спроси преподавателя</h1>
                    <p className="subtitle">
                        Привет, {username}! Задай вопрос по языку — мы ответим и сохраним историю
                        диалога.
                    </p>
                </div>
                <div className="status-badges">
                    <span className="badge">
                        Платформа: <strong>{platform}</strong>
                    </span>
                    <span className="badge">
                        Тема: <strong>{colorScheme}</strong>
                    </span>
                    {telegramUser?.username && (
                        <span className="badge">@{telegramUser.username}</span>
                    )}
                </div>
            </header>

            <section className="chat-panel">
                {historyError && <div className="alert warning">{historyError}</div>}
                {formError && <div className="alert error">{formError}</div>}

                <div className="chat-history">
                    {pagination?.has_more && (
                        <button
                            type="button"
                            className="load-more"
                            disabled={isLoadingHistory}
                            onClick={handleLoadOlder}
                        >
                            {isLoadingHistory ? 'Загружаем...' : 'Показать предыдущие сообщения'}
                        </button>
                    )}

                    {formattedMessages.length === 0 && !isLoadingHistory ? (
                        <div className="empty-state">
                            <p>История пока пустая. Спроси что-нибудь у преподавателя!</p>
                        </div>
                    ) : (
                        formattedMessages.map((message) => (
                            <div key={message.id} className={`message ${message.role}`}>
                                <div className="message-meta">
                                    <span className="role">
                                        {message.role === 'assistant' ? 'Lang Agent' : 'Вы'}
                                    </span>
                                    <span className="timestamp">{message.formattedTime}</span>
                                </div>
                                <p className="message-text">{message.content}</p>
                            </div>
                        ))
                    )}
                </div>

                <form className="chat-form" onSubmit={handleSubmit}>
                    <label htmlFor="message">Ваш вопрос</label>
                    <textarea
                        id="message"
                        value={messageText}
                        placeholder="Например: «Как задать вопрос о дороге во Франции?»"
                        onChange={(event) => setMessageText(event.target.value)}
                        disabled={!isAuthReady || isSending}
                        rows={3}
                    />
                    <button
                        type="submit"
                        disabled={!isAuthReady || isSending || !messageText.trim()}
                    >
                        {isSending ? 'Отправляем...' : 'Спросить'}
                    </button>
                </form>
            </section>
        </div>
    );
};
