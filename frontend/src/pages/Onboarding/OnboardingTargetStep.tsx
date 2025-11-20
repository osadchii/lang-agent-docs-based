import { useState } from 'react';
import { Badge, Button } from '../../components/ui';
import { OnboardingStep } from './OnboardingStep';
import { useOnboardingFlow } from './useOnboardingFlow';
import styles from './OnboardingPage.module.css';

const focuses = [
    { id: 'speaking', label: 'Говорение', hint: 'Диалоги, small talk, стрик' },
    { id: 'vocabulary', label: 'Словарь', hint: 'Карточки, тематические подборки' },
    { id: 'grammar', label: 'Грамматика', hint: 'Короткие правила и практика' },
];

export const OnboardingTargetStep = () => {
    const { goNext, goPrev } = useOnboardingFlow();
    const [selected, setSelected] = useState<string>('speaking');

    return (
        <OnboardingStep
            title="Главный фокус"
            description="Мы настроим подбор заданий и подсказок под выбранный приоритет."
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
                {focuses.map((focus) => (
                    <Button
                        key={focus.id}
                        variant={selected === focus.id ? 'secondary' : 'ghost'}
                        className={styles.optionButton}
                        fullWidth
                        onClick={() => setSelected(focus.id)}
                    >
                        <span>
                            {focus.label} <Badge variant="warning">{focus.hint}</Badge>
                        </span>
                        {selected === focus.id && <span aria-hidden>✓</span>}
                    </Button>
                ))}
            </div>
        </OnboardingStep>
    );
};
