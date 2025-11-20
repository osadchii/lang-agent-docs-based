import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useEffect, useMemo, useRef, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { getNextCard, rateCard } from '../../api/cards';
import { fetchDecks } from '../../api/decks';
import { queryKeys } from '../../api/queryKeys';
import { QueryState } from '../../components/state/QueryState';
import { Badge, Button } from '../../components/ui';
import { useToast } from '../../components/ui/Toast';
import { useHapticFeedback } from '../../hooks/useHapticFeedback';
import type { CardRating } from '../../types/api';
import { classNames } from '../../utils/classNames';
import styles from './CardSessionPage.module.css';

export const CardSessionPage = () => {
    const [flippedCardId, setFlippedCardId] = useState<string | null>(null);
    const startedAtRef = useRef<number | null>(null);
    const [searchParams] = useSearchParams();
    const deckId = searchParams.get('deck_id');

    const navigate = useNavigate();
    const toast = useToast();
    const queryClient = useQueryClient();
    const { notify, impact } = useHapticFeedback();

    const decksQuery = useQuery({
        queryKey: queryKeys.decks(null),
        queryFn: () => fetchDecks(null),
        staleTime: 20 * 1000,
        refetchOnWindowFocus: false,
    });
    const decks = useMemo(() => decksQuery.data ?? [], [decksQuery.data]);
    const currentDeck = useMemo(
        () => decks.find((item) => item.id === deckId) ?? decks.find((item) => item.is_active),
        [deckId, decks],
    );

    const nextCardQuery = useQuery({
        queryKey: queryKeys.nextCard(deckId ?? currentDeck?.id ?? null),
        queryFn: () => getNextCard(deckId ?? currentDeck?.id ?? null),
        refetchOnWindowFocus: false,
    });

    const ratingMutation = useMutation({
        mutationFn: (rating: CardRating) => {
            const startedAt = startedAtRef.current;
            const elapsedSeconds =
                startedAt === null
                    ? undefined
                    : Math.max(1, Math.round((performance.now() - startedAt) / 1000));
            return rateCard({
                card_id: nextCardQuery.data!.id,
                rating,
                duration_seconds: elapsedSeconds,
            });
        },
        onSuccess: async (_response, rating) => {
            if (rating === 'know') {
                notify('success');
            } else if (rating === 'dont_know') {
                notify('error');
            } else {
                impact('medium');
            }
            await queryClient.invalidateQueries({ queryKey: queryKeys.decks(null) });
            setFlippedCardId(null);
            await nextCardQuery.refetch();
        },
        onError: (error: Error) => {
            toast.error('Не удалось сохранить оценку', error.message);
        },
    });

    const card = nextCardQuery.data;
    const flipped = card ? flippedCardId === card.id : false;

    useEffect(() => {
        if (card) {
            startedAtRef.current = performance.now();
        }
    }, [card]);

    const handleFlip = () => {
        if (!card) {
            return;
        }
        setFlippedCardId((value) => (value === card.id ? null : card.id));
        impact('light');
    };

    const handleRate = (rating: CardRating) => {
        if (!card || ratingMutation.isPending) {
            return;
        }
        ratingMutation.mutate(rating);
    };

    const goBack = () => navigate('/practice/cards');

    if (nextCardQuery.isError) {
        return (
            <QueryState
                variant="error"
                title="Не удалось загрузить карточку"
                description="Попробуйте обновить страницу или вернитесь позже."
                actionLabel="Назад"
                onAction={goBack}
            />
        );
    }

    if (nextCardQuery.isPending) {
        return <div className={styles.placeholder}>Загружаем карточки…</div>;
    }

    if (!card) {
        return (
            <QueryState
                variant="empty"
                title="На сегодня карточек нет"
                description="Добавьте новые слова или попробуйте выбрать другую колоду."
                actionLabel="К карточкам"
                onAction={goBack}
            />
        );
    }

    return (
        <div className={styles.session}>
            <div className={styles.topBar}>
                <div>
                    <div className={styles.caption}>Колода</div>
                    <div className={styles.deckName}>{currentDeck?.name ?? 'Выбранная колода'}</div>
                </div>
                <Badge variant="info">{card.status === 'new' ? 'Новая' : 'Повторение'}</Badge>
            </div>

            <div
                className={classNames(styles.flashcard, flipped && styles.flipped)}
                role="button"
                tabIndex={0}
                onClick={handleFlip}
                onKeyDown={(event) => {
                    if (event.key === 'Enter' || event.key === ' ') {
                        event.preventDefault();
                        handleFlip();
                    }
                }}
            >
                <div className={classNames(styles.face, styles.front)}>
                    <div className={styles.word}>{card.word}</div>
                    <div className={styles.example}>{card.example}</div>
                    <div className={styles.hint}>Нажмите, чтобы увидеть перевод</div>
                </div>
                <div className={classNames(styles.face, styles.back)}>
                    <div className={styles.translation}>{card.translation}</div>
                    <div className={styles.example}>{card.example}</div>
                    <div className={styles.exampleSecondary}>{card.example_translation}</div>
                    <div className={styles.hint}>Дайте оценку, чтобы продолжить</div>
                </div>
            </div>

            <div className={styles.ratingRow} aria-label="Оценка карточки">
                <Button
                    variant="ghost"
                    fullWidth
                    className={classNames(styles.ratingButton, styles.danger)}
                    disabled={!flipped || ratingMutation.isPending}
                    onClick={() => handleRate('dont_know')}
                >
                    ❌ Не знаю
                </Button>
                <Button
                    variant="secondary"
                    fullWidth
                    className={styles.ratingButton}
                    disabled={!flipped || ratingMutation.isPending}
                    onClick={() => handleRate('repeat')}
                >
                    🔁 Повторить
                </Button>
                <Button
                    fullWidth
                    className={classNames(styles.ratingButton, styles.success)}
                    disabled={!flipped || ratingMutation.isPending}
                    loading={ratingMutation.isPending}
                    onClick={() => handleRate('know')}
                >
                    ✅ Знаю
                </Button>
            </div>
        </div>
    );
};
