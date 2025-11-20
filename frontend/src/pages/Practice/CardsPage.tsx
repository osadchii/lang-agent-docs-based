import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { createCards, fetchCards } from '../../api/cards';
import { fetchDecks } from '../../api/decks';
import { fetchProfiles } from '../../api/profiles';
import { queryKeys } from '../../api/queryKeys';
import { QueryState } from '../../components/state/QueryState';
import { Badge, Button, Card, Modal, Progress, Tabs } from '../../components/ui';
import { useToast } from '../../components/ui/Toast';
import { useHapticFeedback } from '../../hooks/useHapticFeedback';
import type { CardStatus, Deck, LanguageProfile } from '../../types/api';
import { classNames } from '../../utils/classNames';
import styles from './CardsPage.module.css';

type TabId = 'study' | 'decks';

const splitWords = (raw: string): string[] =>
    raw
        .split(/\n|,/)
        .map((word) => word.trim())
        .filter(Boolean);

const activeProfile = (profiles: LanguageProfile[]): LanguageProfile | null =>
    profiles.find((profile) => profile.is_active) ?? profiles[0] ?? null;

const activeDeck = (decks: Deck[]): Deck | null =>
    decks.find((deck) => deck.is_active) ?? decks[0] ?? null;

const statusLabel = (status: CardStatus) => {
    if (status === 'learning') return 'Повторить';
    if (status === 'review') return 'В работе';
    return 'Новая';
};

export const CardsPage = () => {
    const navigate = useNavigate();
    const queryClient = useQueryClient();
    const toast = useToast();
    const { selectionChanged, notify } = useHapticFeedback();

    const [tab, setTab] = useState<TabId>('study');
    const [addModalOpen, setAddModalOpen] = useState(false);
    const [wordsDraft, setWordsDraft] = useState('');
    const [selectedDeckId, setSelectedDeckId] = useState<string | null>(null);

    const profilesQuery = useQuery({
        queryKey: queryKeys.profiles,
        queryFn: fetchProfiles,
        staleTime: 5 * 60 * 1000,
    });
    const profile = useMemo(() => activeProfile(profilesQuery.data ?? []), [profilesQuery.data]);

    const decksQuery = useQuery({
        queryKey: queryKeys.decks(profile?.id ?? null),
        queryFn: () => fetchDecks(profile?.id ?? null),
        enabled: Boolean(profile),
        staleTime: 20 * 1000,
    });
    const decks = useMemo(() => decksQuery.data ?? [], [decksQuery.data]);
    const deck = useMemo(() => activeDeck(decks), [decks]);

    const cardsPreviewQuery = useQuery({
        queryKey: deck ? queryKeys.cards(deck.id) : ['cards', 'none'],
        queryFn: () => fetchCards({ deckId: deck!.id, limit: 5, offset: 0 }),
        enabled: Boolean(deck),
        staleTime: 15 * 1000,
    });
    const previewCards = cardsPreviewQuery.data?.data ?? [];

    const deckIdForActions = selectedDeckId ?? deck?.id ?? null;
    const studyTotal = deck ? deck.due_cards_count + deck.new_cards_count : 0;
    const tabs: { id: TabId; label: string }[] = [
        { id: 'study', label: 'Учить' },
        { id: 'decks', label: 'Колоды' },
    ];

    const createCardsMutation = useMutation({
        mutationFn: (words: string[]) =>
            createCards({
                deck_id: deckIdForActions ?? '',
                words,
            }),
        onSuccess: async (result) => {
            toast.success('Карточки добавлены', `Создали ${result.created.length}`);
            if (result.duplicates.length > 0) {
                toast.info('Совпадения пропущены', result.duplicates.join(', '));
            }
            setWordsDraft('');
            setAddModalOpen(false);
            await Promise.all([
                queryClient.invalidateQueries({ queryKey: queryKeys.decks(profile?.id ?? null) }),
                result.created[0]?.deck_id
                    ? queryClient.invalidateQueries({
                          queryKey: queryKeys.cards(result.created[0].deck_id),
                      })
                    : Promise.resolve(),
            ]);
        },
        onError: (error: Error) => {
            toast.error('Не удалось добавить карточки', error.message);
        },
    });

    const startSession = () => {
        selectionChanged();
        if (deck) {
            navigate(`/practice/cards/study?deck_id=${deck.id}`);
        }
    };

    const submitWords = () => {
        const words = splitWords(wordsDraft);
        if (!words.length || !deckIdForActions) {
            return;
        }
        createCardsMutation.mutate(words);
    };

    const renderStudyTab = () => {
        if (decksQuery.isError) {
            return (
                <QueryState
                    variant="error"
                    title="Не получилось загрузить колоды"
                    onAction={() => decksQuery.refetch()}
                    actionLabel="Повторить"
                />
            );
        }

        if (decksQuery.isPending || !deck) {
            return <Card className={styles.skeleton} elevated />;
        }

        return (
            <>
                <Card
                    className={styles.hero}
                    gradient
                    title="Режим карточек"
                    subtitle={deck.name}
                    footer={
                        <div className={styles.heroFooter}>
                            <Badge variant="info">Новых: {deck.new_cards_count}</Badge>
                            <Badge variant="warning">К повторению: {deck.due_cards_count}</Badge>
                        </div>
                    }
                >
                    <div className={styles.heroBody}>
                        <div className={styles.statBlock}>
                            <div className={styles.statLabel}>Прогресс колоды</div>
                            <Progress
                                value={
                                    deck.cards_count > 0
                                        ? Math.round(
                                              ((deck.cards_count - deck.new_cards_count) /
                                                  deck.cards_count) *
                                                  100,
                                          )
                                        : 0
                                }
                                showValue
                            />
                            <div className={styles.caption}>
                                {deck.cards_count} карточек • {deck.new_cards_count} новых
                            </div>
                        </div>

                        <div className={styles.actionsRow}>
                            <Button
                                fullWidth
                                disabled={studyTotal === 0}
                                onClick={startSession}
                                icon="🃏"
                            >
                                {studyTotal === 0 ? 'Нет карточек на сегодня' : 'Начать изучение'}
                            </Button>
                            <Button
                                variant="secondary"
                                onClick={() => {
                                    notify('selection');
                                    setAddModalOpen(true);
                                }}
                            >
                                Добавить
                            </Button>
                        </div>
                    </div>
                </Card>

                <Card className={styles.dashboard} padding="lg" elevated>
                    <div className={styles.dashboardRow}>
                        <div>
                            <div className={styles.sectionLabel}>Активная колода</div>
                            <div className={styles.deckName}>{deck.name}</div>
                            {deck.description && (
                                <div className={styles.caption}>{deck.description}</div>
                            )}
                        </div>
                        <div className={styles.badgeStack}>
                            <Badge variant="success">Карточек: {deck.cards_count}</Badge>
                            <Badge variant="warning">Сегодня: {studyTotal}</Badge>
                        </div>
                    </div>
                </Card>

                {studyTotal === 0 && (
                    <QueryState
                        variant="empty"
                        title="На сегодня всё"
                        description="Добавьте новые слова или загляните завтра."
                        actionLabel="Добавить карточки"
                        onAction={() => setAddModalOpen(true)}
                    />
                )}

                {previewCards.length > 0 && (
                    <Card className={styles.previewCard} padding="lg" elevated>
                        <div className={styles.sectionLabel}>Последние карточки</div>
                        <div className={styles.previewList}>
                            {previewCards.map((item) => (
                                <div key={item.id} className={styles.previewItem}>
                                    <div>
                                        <div className={styles.deckName}>{item.word}</div>
                                        <div className={styles.caption}>{item.translation}</div>
                                    </div>
                                    <Badge variant="secondary">{statusLabel(item.status)}</Badge>
                                </div>
                            ))}
                        </div>
                    </Card>
                )}
            </>
        );
    };

    const renderDecksTab = () => {
        if (decksQuery.isError) {
            return (
                <QueryState
                    variant="error"
                    title="Не удалось получить колоды"
                    onAction={() => decksQuery.refetch()}
                    actionLabel="Повторить"
                />
            );
        }

        if (decksQuery.isPending) {
            return <Card className={styles.skeleton} elevated />;
        }

        if (decks.length === 0) {
            return (
                <QueryState
                    variant="empty"
                    title="Колоды не созданы"
                    description="Создайте первую колоду и начните добавлять карточки."
                    actionLabel="Добавить"
                    onAction={() => setAddModalOpen(true)}
                />
            );
        }

        return (
            <div className={styles.deckGrid}>
                {decks.map((item) => (
                    <Card
                        key={item.id}
                        className={classNames(styles.deckCard, item.is_active && styles.activeDeck)}
                        interactive
                        onClick={() => setSelectedDeckId(item.id)}
                        footer={
                            <div className={styles.deckFooter}>
                                <Badge variant="info">Новых: {item.new_cards_count}</Badge>
                                <Badge variant="warning">Сегодня: {item.due_cards_count}</Badge>
                                {item.is_group && <Badge variant="secondary">Групповая</Badge>}
                            </div>
                        }
                    >
                        <div className={styles.deckHeader}>
                            <div>
                                <div className={styles.deckName}>{item.name}</div>
                                <div className={styles.caption}>
                                    {item.cards_count} карточек • активна:{' '}
                                    {item.is_active ? 'да' : 'нет'}
                                </div>
                            </div>
                            <Button
                                size="sm"
                                variant="secondary"
                                onClick={(event) => {
                                    event.stopPropagation();
                                    setSelectedDeckId(item.id);
                                    setAddModalOpen(true);
                                }}
                            >
                                Добавить
                            </Button>
                        </div>
                    </Card>
                ))}
            </div>
        );
    };

    const deckOptions = decks.map((item) => (
        <option key={item.id} value={item.id}>
            {item.name} {item.is_active ? '• активная' : ''}
        </option>
    ));

    const parsedWords = splitWords(wordsDraft);

    return (
        <div className={styles.page}>
            <div className={styles.header}>
                <div>
                    <div className={styles.title}>Карточки</div>
                    <div className={styles.subtitle}>
                        Добавляйте новые слова и проходите короткие сессии
                    </div>
                </div>
                <Button variant="ghost" size="sm" onClick={() => setAddModalOpen(true)}>
                    + Добавить
                </Button>
            </div>

            <Tabs
                tabs={tabs}
                activeTab={tab}
                onChange={(id) => setTab(id as TabId)}
                className={styles.tabs}
            />

            {tab === 'study' ? renderStudyTab() : renderDecksTab()}

            <Modal
                open={addModalOpen}
                onClose={() => setAddModalOpen(false)}
                title="Добавить карточки"
                subtitle="Слова через запятую или с новой строки"
                type="bottomSheet"
                footer={
                    <div className={styles.modalFooter}>
                        <Button
                            fullWidth
                            disabled={
                                parsedWords.length === 0 ||
                                createCardsMutation.isPending ||
                                !deckIdForActions
                            }
                            loading={createCardsMutation.isPending}
                            onClick={submitWords}
                        >
                            Добавить {parsedWords.length > 0 ? parsedWords.length : ''} карточек
                        </Button>
                    </div>
                }
            >
                <div className={styles.modalContent}>
                    <label className={styles.selectLabel} htmlFor="deck-select">
                        Колода
                    </label>
                    <select
                        id="deck-select"
                        className={styles.select}
                        value={selectedDeckId ?? deck?.id ?? ''}
                        onChange={(event) => setSelectedDeckId(event.target.value)}
                    >
                        {deckOptions}
                    </select>

                    <label className={styles.selectLabel} htmlFor="words-input">
                        Слова списком
                    </label>
                    <textarea
                        id="words-input"
                        className={styles.textarea}
                        placeholder="casa\nviajar\naprender"
                        value={wordsDraft}
                        onChange={(event) => setWordsDraft(event.target.value)}
                        rows={5}
                    />
                    <div className={styles.caption}>
                        Слова будут дополнены переводом и примером автоматически.
                    </div>
                </div>
            </Modal>
        </div>
    );
};
