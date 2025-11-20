import { Badge, Button } from '../../components/ui';
import { OnboardingStep } from './OnboardingStep';
import { useOnboardingFlow } from './useOnboardingFlow';
import styles from './OnboardingPage.module.css';

const highlights = [
    {
        title: 'Создадим профиль',
        note: 'Выберем язык, уровни и цели без лишних действий',
    },
    {
        title: 'Синхронизируемся с ботом',
        note: 'Активный профиль сразу доступен в Телеграм',
    },
    {
        title: 'Сохраним прогресс',
        note: 'Подтянем историю и стрик, если он уже был',
    },
];

export const OnboardingWelcomeStep = () => {
    const { goNext, submitting } = useOnboardingFlow();

    return (
        <OnboardingStep
            title="Добро пожаловать в LangAgent"
            description="За 2 минуты настроим обучение и подготовим первый профиль."
            actions={
                <>
                    <Badge variant="success">Нужно меньше 2 минут</Badge>
                    <Button onClick={goNext} disabled={submitting}>
                        Начать настройку
                    </Button>
                </>
            }
        >
            <div className={styles.checklist}>
                {highlights.map((item) => (
                    <div key={item.title} className={styles.checklistItem}>
                        <span className={styles.checkIcon} aria-hidden>
                            ✓
                        </span>
                        <div>
                            <div className={styles.checkTitle}>{item.title}</div>
                            <div className={styles.checkNote}>{item.note}</div>
                        </div>
                    </div>
                ))}
            </div>
        </OnboardingStep>
    );
};
