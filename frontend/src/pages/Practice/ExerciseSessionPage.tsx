import { useState } from 'react';
import { Badge, Button, Card } from '../../components/ui';
import { useHapticFeedback } from '../../hooks/useHapticFeedback';
import { useMainButton } from '../../hooks/useMainButton';
import styles from './PracticePage.module.css';

export const ExerciseSessionPage = () => {
    const [step, setStep] = useState(1);
    const { impact, notify } = useHapticFeedback();

    const handleNext = () => {
        const nextStep = step + 1;
        if (nextStep > 3) {
            notify('success');
        } else {
            impact('light');
        }
        setStep(nextStep > 3 ? 1 : nextStep);
    };

    useMainButton({
        text: step > 3 ? 'Завершить' : 'Ответить',
        isVisible: true,
        isActive: true,
        loading: false,
        onClick: handleNext,
    });

    return (
        <div className={styles.section}>
            <Card
                title="Практика речи"
                subtitle="Отвечайте голосом или текстом, мы дадим фидбек"
                padding="lg"
                elevated
            >
                <div className={styles.sessionBox}>
                    <div className={styles.row}>
                        <Badge variant="success">Шаг {step} / 3</Badge>
                        <Badge variant="info">Тема: путешествия</Badge>
                    </div>
                    <div className={styles.sectionTitle}>
                        Расскажите, куда бы вы поехали весной?
                    </div>
                    <div className={styles.muted}>
                        Коротко опишите маршрут. Если не знаете, нажмите "Подсказка" — покажем
                        пример.
                    </div>
                    <div className={styles.controls}>
                        <Button variant="ghost" size="sm" onClick={() => impact('soft')}>
                            Подсказка
                        </Button>
                        <Button size="sm" variant="secondary" onClick={() => notify('warning')}>
                            Сложно
                        </Button>
                        <Button size="sm" onClick={handleNext}>
                            Ответить
                        </Button>
                    </div>
                </div>
            </Card>
        </div>
    );
};
