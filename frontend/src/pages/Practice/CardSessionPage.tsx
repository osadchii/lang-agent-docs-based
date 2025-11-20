import { useState } from 'react';
import { Badge, Button, Card } from '../../components/ui';
import { useHapticFeedback } from '../../hooks/useHapticFeedback';
import { useMainButton } from '../../hooks/useMainButton';
import styles from './PracticePage.module.css';

type Rating = 'know' | 'repeat' | 'dontKnow';

export const CardSessionPage = () => {
    const [status, setStatus] = useState<'idle' | 'completed'>('idle');
    const { notify, impact } = useHapticFeedback();

    const handleFinish = () => {
        notify('success');
        setStatus('completed');
    };

    useMainButton({
        text: status === 'completed' ? 'Вернуться' : 'Завершить сессию',
        isVisible: true,
        isActive: true,
        loading: false,
        onClick: handleFinish,
    });

    const handleRate = (rating: Rating) => {
        if (rating === 'know') {
            notify('success');
        } else if (rating === 'dontKnow') {
            notify('error');
        } else {
            impact('medium');
        }
    };

    return (
        <div className={styles.section}>
            <Card
                title="Карточка 3/10"
                subtitle="Тренируем связки на тему путешествий"
                padding="lg"
                elevated
            >
                <div className={styles.sessionBox}>
                    <div className={styles.row}>
                        <Badge variant="info">EN → RU</Badge>
                        <Badge variant="warning">Новых: 3</Badge>
                    </div>
                    <div className={styles.sectionTitle}>"to miss out on"</div>
                    <div className={styles.muted}>
                        Не успеть, упустить возможность из-за промедления.
                    </div>
                    <div className={styles.ratingRow}>
                        <Button variant="ghost" onClick={() => handleRate('dontKnow')}>
                            Не знаю
                        </Button>
                        <Button variant="secondary" onClick={() => handleRate('repeat')}>
                            Повторить
                        </Button>
                        <Button onClick={() => handleRate('know')}>Знаю</Button>
                    </div>
                </div>
            </Card>
        </div>
    );
};
