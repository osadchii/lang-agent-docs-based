import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { activateProfile, fetchProfiles } from '../../api/profiles';
import { fetchStats, fetchStreak } from '../../api/stats';
import { queryKeys } from '../../api/queryKeys';
import { Header } from '../../components/layout/Header/Header';
import { QueryState } from '../../components/state/QueryState';
import { Badge, Button, Card, Progress, Skeleton } from '../../components/ui';
import { useHapticFeedback } from '../../hooks/useHapticFeedback';
import { useTelegram } from '../../hooks/useTelegram';
import { useAuthContext } from '../../providers/AuthProvider';
import type { ActivityEntry, LanguageProfile } from '../../types/api';
import { classNames } from '../../utils/classNames';
import styles from './HomePage.module.css';

const DAILY_CARD_GOAL = 12;
const DAILY_EXERCISE_GOAL = 4;
const DAILY_TIME_GOAL = 20;

const todayKey = () => new Date().toISOString().slice(0, 10);

const toDate = (value: string) => new Date(`${value}T00:00:00Z`);

const formatDateLabel = (value: string) => {
    const target = toDate(value);
    const today = toDate(todayKey());
    const yesterday = new Date(today);
    yesterday.setDate(today.getDate() - 1);

    if (target.toDateString() === today.toDateString()) {
        return 'Сегодня';
    }
    if (target.toDateString() === yesterday.toDateString()) {
        return 'Вчера';
    }

    return new Intl.DateTimeFormat('ru-RU', { day: 'numeric', month: 'short' }).format(target);
};

const ratio = (value: number, goal: number) =>
    goal <= 0 ? 0 : Math.min(100, Math.round((value / goal) * 100));

const activityHighlight = (entry: ActivityEntry) => {
    const parts: string[] = [];
    if (entry.cards_studied > 0) {
        parts.push(`Карточки: ${entry.cards_studied}`);
    }
    if (entry.exercises_completed > 0) {
        parts.push(`Упражнения: ${entry.exercises_completed}`);
    }
    if (entry.time_minutes > 0) {
        parts.push(`${entry.time_minutes} мин`);
    }
    return parts.join(' · ');
};

export const HomePage = () => {
    const navigate = useNavigate();
    const queryClient = useQueryClient();
    const { selectionChanged } = useHapticFeedback();
    const { user, isAuthenticated } = useAuthContext();
    const { platform, colorScheme } = useTelegram();

    const profilesQuery = useQuery({
        queryKey: queryKeys.profiles,
        queryFn: fetchProfiles,
        enabled: isAuthenticated,
        staleTime: 5 * 60 * 1000,
    });

    const profiles = useMemo(() => profilesQuery.data ?? [], [profilesQuery.data]);
    const activeProfile = useMemo<LanguageProfile | null>(
        () => profiles.find((profile) => profile.is_active) ?? profiles[0] ?? null,
        [profiles],
    );
    const profileId = activeProfile?.id ?? null;

    const statsQuery = useQuery({
        queryKey: queryKeys.stats(profileId),
        queryFn: () => fetchStats({ profileId }),
        enabled: Boolean(profileId),
        staleTime: 20 * 1000,
        refetchOnMount: 'always',
        refetchOnWindowFocus: true,
    });

    const streakQuery = useQuery({
        queryKey: queryKeys.streak(profileId),
        queryFn: () => fetchStreak(profileId),
        enabled: Boolean(profileId),
        staleTime: 30 * 1000,
        refetchOnMount: 'always',
        refetchOnWindowFocus: true,
    });

    const activateProfileMutation = useMutation({
        mutationFn: (nextProfileId: string) => activateProfile(nextProfileId),
        onSuccess: async (_, nextProfileId) => {
            await Promise.all([
                queryClient.invalidateQueries({ queryKey: queryKeys.profiles }),
                queryClient.invalidateQueries({ queryKey: queryKeys.stats(nextProfileId) }),
                queryClient.invalidateQueries({ queryKey: queryKeys.streak(nextProfileId) }),
            ]);
        },
    });

    const greeting = useMemo(() => {
        const hour = new Date().getHours();
        if (hour < 12) return 'Доброе утро';
        if (hour < 18) return 'Добрый день';
        return 'Добрый вечер';
    }, []);

    const todayStats = useMemo(() => {
        if (!statsQuery.data) return null;
        return statsQuery.data.activity.find((entry) => entry.date === todayKey()) ?? null;
    }, [statsQuery.data]);

    const recentActivity = useMemo<ActivityEntry[]>(() => {
        if (!statsQuery.data) return [];
        return statsQuery.data.activity
            .filter(
                (entry) =>
                    entry.cards_studied > 0 ||
                    entry.exercises_completed > 0 ||
                    entry.time_minutes > 0,
            )
            .sort((a, b) => toDate(b.date).getTime() - toDate(a.date).getTime())
            .slice(0, 3);
    }, [statsQuery.data]);

    const streakValue = streakQuery.data?.current_streak ?? activeProfile?.progress.streak ?? 0;
    const cardsToday = todayStats?.cards_studied ?? 0;
    const exercisesToday = todayStats?.exercises_completed ?? 0;
    const timeToday = todayStats?.time_minutes ?? 0;
    const todayCompleted =
        streakQuery.data?.today_completed ?? cardsToday + exercisesToday + timeToday > 0;

    const cardsProgress = statsQuery.data?.cards ?? null;
    const cardProgressValue =
        cardsProgress && cardsProgress.total > 0
            ? Math.round((cardsProgress.studied / cardsProgress.total) * 100)
            : 0;

    const handleQuickNav = (path: string) => {
        selectionChanged();
        navigate(path);
    };

    const handleProfileChange = (nextProfileId: string) => {
        if (!nextProfileId || nextProfileId === profileId) {
            return;
        }
        activateProfileMutation.mutate(nextProfileId);
    };

    if (profilesQuery.isError) {
        return (
            <QueryState
                variant="error"
                title="Не удалось загрузить профили"
                description="Обновите страницу или попробуйте позже."
                actionLabel="Повторить"
                onAction={() => profilesQuery.refetch()}
            />
        );
    }

    return (
        <div className={styles.screen}>
            <Header
                title="Главная"
                subtitle="Быстрые действия и ваш прогресс за день"
                actions={
                    <div className={styles.headerBadges}>
                        <Badge variant="info" size="md">
                            {platform}
                        </Badge>
                        <Badge variant="warning" size="md">
                            {colorScheme === 'dark' ? 'Тёмная' : 'Светлая'} тема
                        </Badge>
                    </div>
                }
            />

            <Card
                gradient
                elevated
                className={styles.hero}
                title={`${greeting}, ${user?.first_name ?? 'друг'}!`}
                subtitle="Синхронизировано с ботом и профилями Telegram"
                footer={
                    <div className={styles.heroFooter}>
                        <Badge variant="success">Стрик: {streakValue} 🔥</Badge>
                        <Badge variant="info">
                            Карточек: {activeProfile?.progress.cards_count ?? 0}
                        </Badge>
                        <Badge variant="warning">
                            Упражнений: {activeProfile?.progress.exercises_count ?? 0}
                        </Badge>
                    </div>
                }
            >
                <div className={styles.heroContent}>
                    {profilesQuery.isPending && <Skeleton height={64} />}
                    {activeProfile && (
                        <div className={styles.profileHeader}>
                            <div>
                                <div className={styles.language}>
                                    {activeProfile.language_name}{' '}
                                    <span>({activeProfile.language.toUpperCase()})</span>
                                </div>
                                <div className={styles.levels}>
                                    {activeProfile.current_level} → {activeProfile.target_level}
                                </div>
                            </div>
                            {profiles.length > 1 && (
                                <div className={styles.profileSelect}>
                                    <label htmlFor="profile-select">Профиль</label>
                                    <select
                                        id="profile-select"
                                        value={profileId ?? ''}
                                        onChange={(event) =>
                                            handleProfileChange(event.target.value)
                                        }
                                        disabled={activateProfileMutation.isPending}
                                    >
                                        {profiles.map((profile) => (
                                            <option key={profile.id} value={profile.id}>
                                                {profile.language_name}{' '}
                                                {profile.is_active ? ' • активный' : ''}
                                            </option>
                                        ))}
                                    </select>
                                </div>
                            )}
                        </div>
                    )}
                    <Progress
                        label="Прогресс уровня"
                        value={cardProgressValue}
                        indeterminate={statsQuery.isPending}
                        showValue
                    />
                </div>
            </Card>

            <section aria-label="Быстрые действия" className={styles.quickSection}>
                <div className={styles.sectionTitle}>Быстрые действия</div>
                <div className={styles.quickGrid}>
                    <Card
                        className={classNames(styles.quickCard, styles.cards)}
                        padding="lg"
                        interactive
                        title="Карточка"
                        subtitle="Закрепить слова из активной колоды"
                        footer={
                            <div className={styles.quickFooter}>
                                <Badge variant="info">
                                    Сегодня: {cardsToday}/{DAILY_CARD_GOAL}
                                </Badge>
                                <Button
                                    size="sm"
                                    variant="secondary"
                                    onClick={() => handleQuickNav('/practice/cards')}
                                >
                                    Учить
                                </Button>
                            </div>
                        }
                    >
                        <div className={styles.quickBody}>
                            <div className={styles.quickLabel}>5 коротких карточек за минуту</div>
                            <Progress
                                value={ratio(cardsToday, DAILY_CARD_GOAL)}
                                indeterminate={statsQuery.isPending}
                            />
                        </div>
                    </Card>
                    <Card
                        className={classNames(styles.quickCard, styles.exercises)}
                        padding="lg"
                        interactive
                        title="Упражнение"
                        subtitle="Свежая тема для практики"
                        footer={
                            <div className={styles.quickFooter}>
                                <Badge variant="warning">
                                    Завершено: {exercisesToday}/{DAILY_EXERCISE_GOAL}
                                </Badge>
                                <Button
                                    size="sm"
                                    variant="secondary"
                                    onClick={() => handleQuickNav('/practice/exercises')}
                                >
                                    Старт
                                </Button>
                            </div>
                        }
                    >
                        <div className={styles.quickBody}>
                            <div className={styles.quickLabel}>Фокус на говорение и ошибки</div>
                            <Progress
                                value={ratio(exercisesToday, DAILY_EXERCISE_GOAL)}
                                indeterminate={statsQuery.isPending}
                            />
                        </div>
                    </Card>
                </div>
            </section>

            <Card className={styles.sectionCard} title="Сегодня" subtitle="Цели на день">
                {statsQuery.isPending ? (
                    <Skeleton height={96} />
                ) : (
                    <>
                        <div className={styles.progressList}>
                            <div className={styles.progressItem}>
                                <div className={styles.progressHeader}>
                                    <span>Карточки</span>
                                    <Badge variant="info">
                                        {cardsToday}/{DAILY_CARD_GOAL}
                                    </Badge>
                                </div>
                                <Progress value={ratio(cardsToday, DAILY_CARD_GOAL)} />
                            </div>
                            <div className={styles.progressItem}>
                                <div className={styles.progressHeader}>
                                    <span>Упражнения</span>
                                    <Badge variant="warning">
                                        {exercisesToday}/{DAILY_EXERCISE_GOAL}
                                    </Badge>
                                </div>
                                <Progress value={ratio(exercisesToday, DAILY_EXERCISE_GOAL)} />
                            </div>
                            <div className={styles.progressItem}>
                                <div className={styles.progressHeader}>
                                    <span>Время</span>
                                    <Badge variant="success">
                                        {timeToday} мин / {DAILY_TIME_GOAL}
                                    </Badge>
                                </div>
                                <Progress value={ratio(timeToday, DAILY_TIME_GOAL)} />
                            </div>
                        </div>
                        <div
                            className={classNames(
                                styles.streakBanner,
                                todayCompleted ? styles.bannerSuccess : styles.bannerWarning,
                            )}
                        >
                            {todayCompleted
                                ? 'Стрик сохранён — можно выдохнуть 🔥'
                                : 'Нужно действие сегодня, чтобы не сбросить стрик'}
                        </div>
                    </>
                )}
            </Card>

            <Card className={styles.sectionCard} title="Недавняя активность">
                {statsQuery.isError && (
                    <QueryState
                        variant="error"
                        title="Не получилось получить статистику"
                        actionLabel="Обновить"
                        onAction={() => statsQuery.refetch()}
                    />
                )}
                {statsQuery.isPending && <Skeleton height={88} />}
                {!statsQuery.isPending && recentActivity.length === 0 && (
                    <QueryState
                        variant="empty"
                        title="Пока нет данных"
                        description="Сделайте карточку или упражнение — и прогресс появится здесь."
                    />
                )}
                {recentActivity.length > 0 && (
                    <ul className={styles.activityList}>
                        {recentActivity.map((entry) => (
                            <li key={entry.date} className={styles.activityItem}>
                                <div className={styles.activityDate}>
                                    <span
                                        className={classNames(
                                            styles.dot,
                                            entry.activity_level &&
                                                styles[`level${entry.activity_level}`],
                                        )}
                                    />
                                    {formatDateLabel(entry.date)}
                                </div>
                                <div className={styles.activityMeta}>
                                    {activityHighlight(entry) || 'Без активностей'}
                                </div>
                            </li>
                        ))}
                    </ul>
                )}
            </Card>
        </div>
    );
};
