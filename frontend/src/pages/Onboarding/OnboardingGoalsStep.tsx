import { Badge, Button } from '../../components/ui';
import { OnboardingStep } from './OnboardingStep';
import { useOnboardingFlow } from './useOnboardingFlow';
import styles from './OnboardingPage.module.css';

const goals = [
    { id: 'speaking', label: 'Говорение', hint: 'Диалоги, small talk, стрик' },
    { id: 'vocabulary', label: 'Словарь', hint: 'Карточки, тематические подборки' },
    { id: 'grammar', label: 'Грамматика', hint: 'Короткие правила и практика' },
];

export const OnboardingGoalsStep = () => {
    const { goNext, goPrev, toggleGoal, form, submitting } = useOnboardingFlow();

    return (
        <OnboardingStep
            title="С чем помочь в первую очередь?"
            description="Можно выбрать несколько направлений — мы сбалансируем план."
            actions={
                <>
                    <Button variant="secondary" onClick={goPrev} disabled={submitting}>
                        Назад
                    </Button>
                    <Button onClick={goNext} disabled={form.goals.length === 0 || submitting}>
                        Дальше
                    </Button>
                </>
            }
        >
            <div className={styles.options}>
                {goals.map((goal) => {
                    const active = form.goals.includes(goal.id);
                    return (
                        <Button
                            key={goal.id}
                            variant={active ? 'secondary' : 'ghost'}
                            className={styles.optionButton}
                            fullWidth
                            onClick={() => toggleGoal(goal.id)}
                            disabled={submitting}
                        >
                            <span>
                                {goal.label} <Badge variant="warning">{goal.hint}</Badge>
                            </span>
                            {active && <span aria-hidden>✓</span>}
                        </Button>
                    );
                })}
            </div>
        </OnboardingStep>
    );
};
