import { useState } from 'react';
import { Badge, Button } from '../../components/ui';
import { OnboardingStep } from './OnboardingStep';
import { useOnboardingFlow } from './useOnboardingFlow';
import styles from './OnboardingPage.module.css';

const routines = [
    { id: 'sprint', label: 'Спринт 10 минут', info: 'Короткие карточки + 1 упражнение' },
    { id: 'steady', label: '25 минут в день', info: 'Карточки, аудио, говорение' },
    { id: 'deep', label: '45 минут', info: 'Продвинутая грамматика + практика' },
];

export const OnboardingGoalStep = () => {
    const { goNext, goPrev } = useOnboardingFlow();
    const [selected, setSelected] = useState<string>('steady');

    return (
        <OnboardingStep
            title="Какой темп выберем?"
            description="Можно менять в любой момент. Мы напомним и подберём нагрузку."
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
                {routines.map((routine) => (
                    <Button
                        key={routine.id}
                        variant={selected === routine.id ? 'secondary' : 'ghost'}
                        className={styles.optionButton}
                        fullWidth
                        onClick={() => setSelected(routine.id)}
                    >
                        <span>
                            {routine.label} <Badge variant="info">{routine.info}</Badge>
                        </span>
                        {selected === routine.id && <span aria-hidden>✓</span>}
                    </Button>
                ))}
            </div>
        </OnboardingStep>
    );
};
