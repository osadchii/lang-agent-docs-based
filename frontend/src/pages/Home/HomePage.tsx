import { useInfiniteQuery, useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { type FormEvent, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { getErrorMessage } from '../../api/errors';
import { queryKeys } from '../../api/queryKeys';
import { fetchChatHistory, sendChatMessage } from '../../api/chat';
import { activateProfile, createProfile, fetchProfiles } from '../../api/profiles';
import { QueryState } from '../../components/state/QueryState';
import { useAuthContext } from '../../providers/AuthProvider';
import { useTelegram } from '../../hooks/useTelegram';
import type { CEFRLevel, ChatMessage, LanguageProfileCreatePayload } from '../../types/api';
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

export const HomePage = () => {
    const { user: telegramUser, platform, colorScheme, isReady } = useTelegram();
    const { user, status: authStatus, error: authError, isAuthenticated } = useAuthContext();
    const queryClient = useQueryClient();

    const [profilesError, setProfilesError] = useState<string | null>(null);
    const [messageText, setMessageText] = useState('');
    const [formError, setFormError] = useState<string | null>(null);
    const [isCreatingProfile, setIsCreatingProfile] = useState(false);
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
    const isAuthReady = authStatus === 'success' || isAuthenticated;
    const isInitialLoading = !isReady || authStatus === 'idle' || authStatus === 'loading';
    const profilesQuery = useQuery({
        queryKey: queryKeys.profiles,
        queryFn: fetchProfiles,
        enabled: isAuthReady,
        staleTime: 5 * 60 * 1000,
    });
    const profiles = useMemo(() => profilesQuery.data ?? [], [profilesQuery.data]);
    const activeProfile = useMemo(
        () => profiles.find((profile) => profile.is_active) ?? profiles[0] ?? null,
        [profiles],
    );
    const profileId = activeProfile?.id ?? null;

    const profilesErrorMessage =
        profilesError ??
        (profilesQuery.error
            ? getErrorMessage(profilesQuery.error, 'Не удалось загрузить профили.')
            : null);

    const chatHistoryQuery = useInfiniteQuery({
        queryKey: queryKeys.chatHistory(profileId),
        enabled: isAuthReady && Boolean(profileId),
        initialPageParam: 0,
        queryFn: ({ pageParam = 0 }) =>
            fetchChatHistory({
                profileId: profileId as string,
                limit: PAGE_SIZE,
                offset: Number(pageParam) || 0,
            }),
        getNextPageParam: (lastPage) =>
            lastPage.pagination.has_more ? lastPage.pagination.next_offset : undefined,
    });

    const chatMessages = useMemo<ChatMessage[]>(() => {
        const pages = chatHistoryQuery.data?.pages ?? [];
        const merged = pages.flatMap((page) => page.messages);
        return merged
            .slice()
            .sort((a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime());
    }, [chatHistoryQuery.data]);

    const historyErrorMessage = chatHistoryQuery.error
        ? getErrorMessage(chatHistoryQuery.error, 'Не удалось загрузить сообщения.')
        : null;

    const profilesLoading = profilesQuery.isPending || profilesQuery.isRefetching;
    const isInitialHistoryLoading = chatHistoryQuery.isPending && Boolean(profileId);
    const isFetchingHistory = chatHistoryQuery.isFetching;
    const isFetchingMoreHistory = chatHistoryQuery.isFetchingNextPage;

    const sendMessageMutation = useMutation({
        mutationFn: (payload: { profileId: string; message: string }) =>
            sendChatMessage({ message: payload.message, profile_id: payload.profileId }),
        onSuccess: async () => {
            setMessageText('');
            await queryClient.invalidateQueries({ queryKey: queryKeys.chatHistory(profileId) });
        },
        onError: (error) => {
            setFormError(
                getErrorMessage(error, 'Не удалось отправить сообщение. Попробуйте ещё раз.'),
            );
        },
    });

    const activateProfileMutation = useMutation({
        mutationFn: (nextProfileId: string) => activateProfile(nextProfileId),
        onSuccess: async () => {
            setProfilesError(null);
            await Promise.all([
                queryClient.invalidateQueries({ queryKey: queryKeys.profiles }),
                queryClient.removeQueries({ queryKey: queryKeys.chatHistoryRoot }),
            ]);
        },
        onError: (error) => {
            setProfilesError(getErrorMessage(error, 'Не удалось переключить профиль.'));
        },
    });

    const createProfileMutation = useMutation({
        mutationFn: (payload: LanguageProfileCreatePayload) => createProfile(payload),
        onSuccess: async () => {
            setIsCreatingProfile(false);
            setProfileForm({ ...defaultProfileForm });
            setProfileFormError(null);
            await queryClient.invalidateQueries({ queryKey: queryKeys.profiles });
        },
        onError: (error) => {
            setProfileFormError(getErrorMessage(error, 'Не удалось создать профиль.'));
        },
    });

    const isSending = sendMessageMutation.isPending;
    const isSavingProfile = createProfileMutation.isPending;

    const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
        event.preventDefault();
        if (!messageText.trim() || !isAuthReady) {
            return;
        }

        if (!profileId) {
            setFormError('Пожалуйста, выберите или создайте профиль.');
            return;
        }

        setFormError(null);
        sendMessageMutation.mutate({ profileId, message: messageText.trim() });
    };

    const handleActivateProfile = (nextProfileId: string) => {
        if (nextProfileId === profileId) {
            return;
        }
        setProfilesError(null);
        activateProfileMutation.mutate(nextProfileId);
    };

    const handleCreateProfile = (event: FormEvent<HTMLFormElement>) => {
        event.preventDefault();
        setProfileFormError(null);
        createProfileMutation.mutate(profileForm);
    };

    const handleLoadOlder = () => {
        if (!chatHistoryQuery.hasNextPage || chatHistoryQuery.isFetchingNextPage) {
            return;
        }
        chatHistoryQuery.fetchNextPage().catch(() => null);
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

    const formattedMessages = useMemo(() => {
        const formatter = new Intl.DateTimeFormat('ru-RU', {
            hour: '2-digit',
            minute: '2-digit',
        });

        return chatMessages.map((message) => ({
            ...message,
            formattedTime: formatter.format(new Date(message.timestamp)),
        }));
    }, [chatMessages]);

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
                    <Link to="/ui-kit" className="ghost-button">
                        UI Kit
                    </Link>
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

                {profilesErrorMessage && (
                    <QueryState
                        variant="error"
                        title="Не удалось загрузить профили"
                        description={profilesErrorMessage}
                        actionLabel="Повторить"
                        onAction={() => profilesQuery.refetch()}
                    />
                )}

                {profilesLoading && profiles.length === 0 && (
                    <QueryState
                        variant="loading"
                        title="Загружаем профили"
                        description="Синхронизируем ваши языки и прогресс."
                    />
                )}

                {!profilesLoading && profiles.length === 0 && !profilesErrorMessage && (
                    <QueryState
                        variant="empty"
                        title="Пока нет профилей"
                        description="Создайте первый профиль, чтобы начать занятия."
                        actionLabel="Создать профиль"
                        onAction={toggleProfileForm}
                    />
                )}

                {profiles.length > 0 && (
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
                                                GOAL_OPTIONS.find((option) => option.value === goal)
                                                    ?.label ?? goal;
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
                                        disabled={
                                            profile.id === profileId ||
                                            activateProfileMutation.isPending
                                        }
                                        onClick={() => handleActivateProfile(profile.id)}
                                    >
                                        {profile.id === profileId ? 'Активный' : 'Сделать активным'}
                                    </button>
                                </div>
                            </li>
                        ))}
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

                        {profileFormError && <div className="alert error">{profileFormError}</div>}

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
                {historyErrorMessage && (
                    <QueryState
                        variant="error"
                        title="Не удалось загрузить сообщения"
                        description={historyErrorMessage}
                        actionLabel="Обновить"
                        onAction={() => chatHistoryQuery.refetch()}
                    />
                )}
                {formError && <div className="alert error">{formError}</div>}

                <div className="chat-history">
                    {profileId && isInitialHistoryLoading && (
                        <QueryState
                            variant="loading"
                            title="Загружаем историю"
                            description="Собираем диалог с ассистентом..."
                        />
                    )}

                    {chatHistoryQuery.hasNextPage && profileId && (
                        <button
                            type="button"
                            className="load-more"
                            disabled={isFetchingMoreHistory}
                            onClick={handleLoadOlder}
                        >
                            {isFetchingMoreHistory ? 'Загружаем...' : 'Показать более ранние'}
                        </button>
                    )}

                    {!profileId ? (
                        <QueryState
                            variant="empty"
                            title="Нет активного профиля"
                            description="Сначала создайте и активируйте профиль, чтобы начать диалог."
                            actionLabel="Создать профиль"
                            onAction={toggleProfileForm}
                        />
                    ) : formattedMessages.length === 0 && !isFetchingHistory ? (
                        <QueryState
                            variant="empty"
                            title="История пока пустая"
                            description="Задайте первый вопрос ассистенту, чтобы начать диалог."
                        />
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
                        disabled={!isAuthReady || isSending || !messageText.trim() || !profileId}
                    >
                        {isSending ? 'Отправляем...' : 'Отправить'}
                    </button>
                </form>
            </section>
        </div>
    );
};
