import { Badge, Button, Card, Progress } from '../../components/ui';
import styles from './PracticePage.module.css';

const featuredDecks = [
    {
        id: 'verb-motion',
        title: 'Глаголы движения',
        level: 'B1',
        dueToday: 14,
        mastered: 62,
        learning: 18,
    },
    { id: 'travel', title: 'Путешествия', level: 'A2', dueToday: 6, mastered: 34, learning: 12 },
    {
        id: 'business',
        title: 'Бизнес-встречи',
        level: 'B2',
        dueToday: 9,
        mastered: 41,
        learning: 21,
    },
];

export const CardsPage = () => {
    return (
        <div className={styles.section}>
            <div>
                <div className={styles.sectionTitle}>Карточки</div>
                <div className={styles.muted}>
                    Учите слова в закатном режиме — короткие серии с вибро.
                </div>
            </div>

            <div className={styles.grid}>
                {featuredDecks.map((deck) => (
                    <Card
                        key={deck.id}
                        className={styles.deckCard}
                        interactive
                        gradient
                        title={deck.title}
                        subtitle={`Уровень ${deck.level}`}
                        footer={
                            <div className={styles.row}>
                                <Badge variant="info">Сегодня: {deck.dueToday}</Badge>
                                <Button size="sm" variant="secondary">
                                    Учить
                                </Button>
                            </div>
                        }
                    >
                        <div className={styles.row}>
                            <div className={styles.pill}>Выучено: {deck.mastered}%</div>
                            <div className={styles.pill}>В прогрессе: {deck.learning}%</div>
                        </div>
                        <Progress value={deck.mastered} label="Прогресс колоды" showValue />
                    </Card>
                ))}
            </div>

            <Card
                title="Быстрый старт"
                subtitle="5 карточек • 45 секунд"
                padding="lg"
                elevated
                footer={
                    <div className={styles.row}>
                        <div className={styles.chip}>Лучше всего утром</div>
                        <Button size="sm" variant="secondary">
                            Настроить
                        </Button>
                    </div>
                }
            >
                <div className={styles.sessionBox}>
                    <div className={styles.row}>
                        <div>
                            <div className={styles.sectionTitle}>Микро-сессия</div>
                            <div className={styles.muted}>
                                Без выхода в меню — сразу в карточки.
                            </div>
                        </div>
                        <Button size="sm">Старт</Button>
                    </div>
                    <div className={styles.row}>
                        <Badge variant="success">Цепочка 5 дней</Badge>
                        <Badge variant="warning">Новых: 8</Badge>
                    </div>
                </div>
            </Card>
        </div>
    );
};
