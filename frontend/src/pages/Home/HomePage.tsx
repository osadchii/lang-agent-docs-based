import { type FormEvent, useCallback, useEffect, useMemo, useState } from 'react';
import { fetchChatHistory, sendChatMessage } from '../../api/chat';
import { activateProfile, createProfile, fetchProfiles } from '../../api/profiles';
import { useAuth } from '../../hooks/useAuth';
import { useTelegram } from '../../hooks/useTelegram';
import type {
    CEFRLevel,
    ChatMessage,
    LanguageProfile,
    LanguageProfileCreatePayload,
    PaginationMeta,
} from '../../types/api';
import './HomePage.css';

const PAGE_SIZE = 20;
const CEFR_LEVELS: CEFRLevel[] = ['A1', 'A2', 'B1', 'B2', 'C1', 'C2'];
const LANGUAGE_OPTIONS = [
    { value: 'en', label: 'Английский' },
    { value: 'es', label: 'Испанский' },
    { value: 'de', label: 'Немецкий' },
    { value: 'fr', label: 'Французский' },
    { value: 'it', label: 'Итальянский' },
    { value: 'pt', label: 'Португальский' },
    { value: 'tr', label: 'Турецкий' },
    { value: 'zh', label: 'Китайский' },
];
const GOAL_OPTIONS = [
    { value: 'communication', label: 'Общение' },
    { value: 'travel', label: 'Путешествия' },
    { value: 'work', label: 'Работа' },
    { value: 'study', label: 'Учёба' },
    { value: 'reading', label: 'Чтение' },
    { value: 'self_development', label: 'Саморазвитие' },
    { value: 'relationships', label: 'Отношения' },
    { value: 'relocation', label: 'Переезд' },
];
const INTERFACE_LANGUAGES = [
    { value: 'ru', label: 'Русский' },
    { value: 'en', label: 'English' },
];

type ApiError = {
    response?: {
        data?: {
            error?: {
                message?: string;
            };
        };
    };
};

const extractErrorMessage = (error: unknown): string => {
    if (
        typeof error === 'object' &&
        error !== null &&
        'response' in error &&
        typeof (error as ApiError).response?.data?.error?.message === 'string'
    ) {
        return (error as ApiError).response?.data?.error?.message as string;
    }
    return 'Не удалось выполнить действие. Попробуйте позже.';
};

export const HomePage = () => {
    const { user: telegramUser, platform, colorScheme, isReady, initData } = useTelegram();
    const { user, status: authStatus, error: authError } = useAuth(initData);

    const [messages, setMessages] = useState<ChatMessage[]>([]);
    const [pagination, setPagination] = useState<PaginationMeta | null>(null);
    const [profiles, setProfiles] = useState<LanguageProfile[]>([]);
    const [profilesError, setProfilesError] = useState<string | null>(null);
    const [profilesLoading, setProfilesLoading] = useState(false);
    const [profileId, setProfileId] = useState<string | null>(null);
    const [messageText, setMessageText] = useState('');
    const [historyError, setHistoryError] = useState<string | null>(null);
    const [formError, setFormError] = useState<string | null>(null);
    const [isLoadingHistory, setIsLoadingHistory] = useState(false);
    const [isSending, setIsSending] = useState(false);
    const [isCreatingProfile, setIsCreatingProfile] = useState(false);
    const [isSavingProfile, setIsSavingProfile] = useState(false);
    const [profileFormError, setProfileFormError] = useState<string | null>(null);
    const defaultProfileForm = useMemo<LanguageProfileCreatePayload>(
        () => ({
            language: 'en',
            current_level: 'A1',
            target_level: 'A2',
            goals: ['communication'],
            interface_language: 'ru',
        }),
        [],
    );
    const [profileForm, setProfileForm] = useState<LanguageProfileCreatePayload>(() => ({
        ...defaultProfileForm,
    }));

    const username = user?.first_name ?? telegramUser?.first_name ?? 'друг';
    const isAuthReady = authStatus === 'success';
    const isInitialLoading = !isReady || authStatus === 'idle' || authStatus === 'loading';
    const activeProfile = useMemo(
        () => profiles.find((profile) => profile.id === profileId) ?? null,
        [profiles, profileId],
    );

    const loadProfiles = useCallback(async () => {
        if (!isAuthReady) {
            return;
        }
        setProfilesLoading(true);
        setProfilesError(null);
        try {
            const items = await fetchProfiles();
            setProfiles(items);
            const active = items.find((item) => item.is_active) ?? items.at(0) ?? null;
            setProfileId(active?.id ?? null);
        } catch (error) {
            console.error('Failed to load profiles', error);
            setProfilesError('Не удалось загрузить профили.');
        } finally {
            setProfilesLoading(false);
        }
    }, [isAuthReady]);

    useEffect(() => {
        if (isAuthReady) {
            loadProfiles().catch(() => null);
        }
    }, [isAuthReady, loadProfiles]);

    const loadHistory = useCallback(
        async (options?: { offset?: number; append?: boolean; profileOverride?: string }) => {
            if (!isAuthReady) {
                return;
            }

            const offset = options?.offset ?? 0;
            const append = options?.append ?? false;
            const profileForRequest = options?.profileOverride ?? profileId;
            if (!profileForRequest) {
                setMessages([]);
                setPagination(null);
                return;
            }

            setIsLoadingHistory(true);
            setHistoryError(null);

            try {
                const response = await fetchChatHistory({
                    profileId: profileForRequest,
                    limit: PAGE_SIZE,
                    offset,
                });

                setMessages((prev) =>
                    append ? [...response.messages, ...prev] : response.messages,
                );
                setPagination(response.pagination);
            } catch (error) {
                console.error('Failed to load history', error);
                setHistoryError('Не удалось загрузить сообщения.');
            } finally {
                setIsLoadingHistory(false);
            }
        },
        [isAuthReady, profileId],
    );

    useEffect(() => {
        if (isAuthReady && profileId) {
            loadHistory({ offset: 0, append: false }).catch(() => null);
        }
    }, [isAuthReady, profileId, loadHistory]);

    const handleLoadOlder = useCallback(() => {
        if (!profileId || !pagination?.has_more || pagination.next_offset == null) {
            return;
        }
        loadHistory({ offset: pagination.next_offset, append: true }).catch(() => null);
    }, [pagination, loadHistory, profileId]);

    const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
        event.preventDefault();
        if (!messageText.trim() || !isAuthReady) {
            return;
        }

        if (!profileId) {
            setFormError('Пожалуйста, выберите или создайте профиль.');
            return;
        }

        setIsSending(true);
        setFormError(null);

        try {
            await sendChatMessage({
                message: messageText.trim(),
                profile_id: profileId,
            });

            setMessageText('');
            await loadHistory({ offset: 0, append: false });
        } catch (error) {
            console.error('Failed to send message', error);
            setFormError('Не удалось отправить сообщение. Попробуйте ещё раз.');
        } finally {
            setIsSending(false);
        }
    };

    const handleActivateProfile = async (nextProfileId: string) => {
        if (nextProfileId === profileId) {
            return;
        }
        setProfilesError(null);
        try {
            await activateProfile(nextProfileId);
            setProfileId(nextProfileId);
            await loadProfiles();
            await loadHistory({ offset: 0, append: false, profileOverride: nextProfileId });
        } catch (error) {
            console.error('Failed to activate profile', error);
            setProfilesError(extractErrorMessage(error));
        }
    };

    const handleCreateProfile = async (event: FormEvent<HTMLFormElement>) => {
        event.preventDefault();
        setProfileFormError(null);
        setIsSavingProfile(true);
        try {
            await createProfile(profileForm);
            setIsCreatingProfile(false);
            setProfileForm({ ...defaultProfileForm });
            await loadProfiles();
        } catch (error) {
            console.error('Failed to create profile', error);
            setProfileFormError(extractErrorMessage(error));
        } finally {
            setIsSavingProfile(false);
        }
    };

    const toggleProfileForm = () => {
        setIsCreatingProfile((prev) => {
            if (prev) {
                setProfileForm({ ...defaultProfileForm });
                setProfileFormError(null);
            }
            return !prev;
        });
    };

    useEffect(() => {
        const currentIndex = CEFR_LEVELS.indexOf(profileForm.current_level);
        const targetIndex = CEFR_LEVELS.indexOf(profileForm.target_level);
        if (targetIndex < currentIndex) {
            setProfileForm((prev) => ({
                ...prev,
                target_level: prev.current_level,
            }));
        }
    }, [profileForm.current_level, profileForm.target_level]);

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

    const availableTargetLevels = useMemo(() => {
        const currentIndex = CEFR_LEVELS.indexOf(profileForm.current_level);
        return CEFR_LEVELS.slice(currentIndex);
    }, [profileForm.current_level]);

    if (isInitialLoading) {
        return (
            <div className="home-page loading">
                <div className="loader" />
                <p>Инициализация Mini App...</p>
            </div>
        );
    }

    if (authStatus === 'error') {
        return (
            <div className="home-page error-state">
                <h2>Не получилось авторизоваться</h2>
                <p>{authError}</p>
                <p className="hint">
                    Убедитесь, что Mini App открыта внутри Telegram и включена автоматическая
                    авторизация.
                </p>
            </div>
        );
    }

    return (
        <div className="home-page">
            <header className="home-header">
                <div>
                    <p className="eyebrow">Lang Agent</p>
                    <h1 className="title">Персональный языковой тренер</h1>
                    <p className="subtitle">
                        Привет, {username}! Выбирайте профиль, ставьте цели и занимайтесь в удобном
                        ритме.
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

            <section className="profiles-panel">
                <div className="profiles-header">
                    <div>
                        <h2>Профили изучения</h2>
                        <p className="profiles-subtitle">
                            Управляйте языками, целями и интерфейсом Mini App.
                        </p>
                    </div>
                    <button type="button" className="ghost-button" onClick={toggleProfileForm}>
                        {isCreatingProfile ? 'Закрыть' : 'Новый профиль'}
                    </button>
                </div>

                {profilesError && <div className="alert error">{profilesError}</div>}

                {profilesLoading && profiles.length === 0 ? (
                    <div className="empty-state">Загружаем профили...</div>
                ) : (
                    <ul className="profile-list">
                        {profiles.map((profile) => (
                            <li
                                key={profile.id}
                                className={`profile-card ${profile.is_active ? 'active' : ''}`}
                            >
                                <div className="profile-info">
                                    <p className="profile-language">
                                        {profile.language_name}{' '}
                                        <span>({profile.language.toUpperCase()})</span>
                                    </p>
                                    <p className="profile-levels">
                                        {profile.current_level} → {profile.target_level}
                                    </p>
                                    <p className="profile-goals">
                                        {profile.goals.map((goal) => {
                                            const label =
                                                GOAL_OPTIONS.find(
                                                    (option) => option.value === goal,
                                                )?.label ?? goal;
                                            return <span key={goal}>{label}</span>;
                                        })}
                                    </p>
                                </div>
                                <div className="profile-actions">
                                    <span className="profile-streak">
                                        🔥 {profile.progress.streak ?? 0}
                                    </span>
                                    <button
                                        type="button"
                                        disabled={profile.id === profileId}
                                        onClick={() => handleActivateProfile(profile.id)}
                                    >
                                        {profile.id === profileId ? 'Активный' : 'Сделать активным'}
                                    </button>
                                </div>
                            </li>
                        ))}

                        {!profilesLoading && profiles.length === 0 && (
                            <li className="profile-card empty">
                                <p>У вас пока нет профилей. Создайте первый, чтобы начать.</p>
                            </li>
                        )}
                    </ul>
                )}

                {isCreatingProfile && (
                    <form className="profile-form" onSubmit={handleCreateProfile}>
                        <div className="profile-form-grid">
                            <label>
                                Язык
                                <select
                                    value={profileForm.language}
                                    onChange={(event) =>
                                        setProfileForm((prev) => ({
                                            ...prev,
                                            language: event.target.value,
                                        }))
                                    }
                                >
                                    {LANGUAGE_OPTIONS.map((option) => (
                                        <option key={option.value} value={option.value}>
                                            {option.label}
                                        </option>
                                    ))}
                                </select>
                            </label>
                            <label>
                                Текущий уровень
                                <select
                                    value={profileForm.current_level}
                                    onChange={(event) =>
                                        setProfileForm((prev) => ({
                                            ...prev,
                                            current_level: event.target.value as CEFRLevel,
                                        }))
                                    }
                                >
                                    {CEFR_LEVELS.map((level) => (
                                        <option key={level} value={level}>
                                            {level}
                                        </option>
                                    ))}
                                </select>
                            </label>
                            <label>
                                Целевой уровень
                                <select
                                    value={profileForm.target_level}
                                    onChange={(event) =>
                                        setProfileForm((prev) => ({
                                            ...prev,
                                            target_level: event.target.value as CEFRLevel,
                                        }))
                                    }
                                >
                                    {availableTargetLevels.map((level) => (
                                        <option key={level} value={level}>
                                            {level}
                                        </option>
                                    ))}
                                </select>
                            </label>
                            <label>
                                Язык интерфейса
                                <select
                                    value={profileForm.interface_language}
                                    onChange={(event) =>
                                        setProfileForm((prev) => ({
                                            ...prev,
                                            interface_language: event.target.value,
                                        }))
                                    }
                                >
                                    {INTERFACE_LANGUAGES.map((option) => (
                                        <option key={option.value} value={option.value}>
                                            {option.label}
                                        </option>
                                    ))}
                                </select>
                            </label>
                        </div>

                        <fieldset className="checkbox-group">
                            <legend>Цели</legend>
                            <div className="checkbox-grid">
                                {GOAL_OPTIONS.map((option) => {
                                    const checked = profileForm.goals.includes(option.value);
                                    return (
                                        <label key={option.value} className="checkbox-item">
                                            <input
                                                type="checkbox"
                                                checked={checked}
                                                onChange={() =>
                                                    setProfileForm((prev) => {
                                                        const includes = prev.goals.includes(
                                                            option.value,
                                                        );
                                                        if (includes && prev.goals.length === 1) {
                                                            return prev;
                                                        }
                                                        const nextGoals = includes
                                                            ? prev.goals.filter(
                                                                  (goal) => goal !== option.value,
                                                              )
                                                            : [...prev.goals, option.value];
                                                        return {
                                                            ...prev,
                                                            goals: nextGoals,
                                                        };
                                                    })
                                                }
                                            />
                                            <span>{option.label}</span>
                                        </label>
                                    );
                                })}
                            </div>
                        </fieldset>

                        {profileFormError && (
                            <div className="alert error">{profileFormError}</div>
                        )}

                        <button type="submit" disabled={isSavingProfile}>
                            {isSavingProfile ? 'Сохраняем...' : 'Создать профиль'}
                        </button>
                    </form>
                )}
            </section>

            <section className="chat-panel">
                {activeProfile && (
                    <div className="active-profile-badge">
                        Активный профиль:{' '}
                        <strong>
                            {activeProfile.language_name} ({activeProfile.current_level} →{' '}
                            {activeProfile.target_level})
                        </strong>
                    </div>
                )}
                {historyError && <div className="alert warning">{historyError}</div>}
                {formError && <div className="alert error">{formError}</div>}

                <div className="chat-history">
                    {pagination?.has_more && profileId && (
                        <button
                            type="button"
                            className="load-more"
                            disabled={isLoadingHistory}
                            onClick={handleLoadOlder}
                        >
                            {isLoadingHistory ? 'Загружаем...' : 'Показать более ранние'}
                        </button>
                    )}

                    {!profileId ? (
                        <div className="empty-state">
                            Сначала создайте профиль, чтобы начать диалог с преподавателем.
                        </div>
                    ) : formattedMessages.length === 0 && !isLoadingHistory ? (
                        <div className="empty-state">
                            <p>История пока пустая. Задайте первый вопрос ассистенту!</p>
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
                        placeholder="Например: “Как спросить дорогу до метро на испанском?”"
                        onChange={(event) => setMessageText(event.target.value)}
                        disabled={!isAuthReady || isSending || !profileId}
                        rows={3}
                    />
                    <button
                        type="submit"
                        disabled={
                            !isAuthReady || isSending || !messageText.trim() || !profileId
                        }
                    >
                        {isSending ? 'Отправляем...' : 'Отправить'}
                    </button>
                </form>
            </section>
        </div>
    );
};
