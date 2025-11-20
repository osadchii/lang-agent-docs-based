import { useState } from 'react';
import { Badge, Button } from '../../components/ui';
import { OnboardingStep } from './OnboardingStep';
import { useOnboardingFlow } from './useOnboardingFlow';
import styles from './OnboardingPage.module.css';

const levels = [
    { id: 'A1', label: 'A1 — начинаю', note: 'Понимаю простые фразы, нужен словарь' },
    { id: 'A2', label: 'A2 — базовый', note: 'О знакомых темах, простые ответы' },
    { id: 'B1', label: 'B1 — продолжаю', note: 'Могу поддержать разговор' },
    { id: 'B2', label: 'B2 — уверенный', note: 'Общаюсь на работе/путешествиях' },
];

export const OnboardingCurrentLevelStep = () => {
    const { goNext, goPrev } = useOnboardingFlow();
    const [selected, setSelected] = useState<string>('B1');

    return (
        <OnboardingStep
            title="Какой у вас сейчас уровень?"
            description="Подберём стартовые блоки и количество новых слов в день."
            actions={
                <>
                    <Button variant="secondary" onClick={goPrev}>
                        Назад
                    </Button>
                    <Button onClick={goNext}>Дальше</Button>
                </>
            }
        >
            <div className={styles.options}>
                {levels.map((level) => (
                    <Button
                        key={level.id}
                        variant={selected === level.id ? 'secondary' : 'ghost'}
                        className={styles.optionButton}
                        fullWidth
                        onClick={() => setSelected(level.id)}
                    >
                        <span>
                            {level.label} <Badge variant="info">{level.note}</Badge>
                        </span>
                        {selected === level.id && <span aria-hidden>✓</span>}
                    </Button>
                ))}
            </div>
        </OnboardingStep>
    );
};
