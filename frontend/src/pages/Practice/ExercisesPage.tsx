import { Badge, Button, Card, Progress } from '../../components/ui';
import styles from './PracticePage.module.css';

const topics = [
    { id: 'speaking', title: 'Говорение', focus: 'Диалоги и small talk', progress: 48 },
    { id: 'grammar', title: 'Грамматика', focus: 'Настоящее / прошедшее', progress: 32 },
    {
        id: 'listening',
        title: 'Аудирование',
        focus: 'Короткие треки по теме путешествий',
        progress: 56,
    },
];

export const ExercisesPage = () => {
    return (
        <div className={styles.section}>
            <div>
                <div className={styles.sectionTitle}>Упражнения</div>
                <div className={styles.muted}>
                    Смешиваем практику: говорение, аудирование, грамматика.
                </div>
            </div>

            <div className={styles.grid}>
                {topics.map((topic) => (
                    <Card
                        key={topic.id}
                        gradient
                        className={styles.deckCard}
                        title={topic.title}
                        subtitle={topic.focus}
                        footer={
                            <div className={styles.row}>
                                <Badge variant="info">15 вопросов</Badge>
                                <Button size="sm" variant="secondary">
                                    Продолжить
                                </Button>
                            </div>
                        }
                    >
                        <Progress value={topic.progress} label="Уверенность" showValue />
                    </Card>
                ))}
            </div>

            <Card
                elevated
                title="Режим без отвлечений"
                subtitle="Закрывает BottomNav, включает вибро и MainButton для ключевых действий"
            >
                <div className={styles.row}>
                    <div className={styles.muted}>Открываемся на полный экран для упражнений.</div>
                    <Button size="sm" variant="ghost">
                        Подробнее
                    </Button>
                </div>
            </Card>
        </div>
    );
};
