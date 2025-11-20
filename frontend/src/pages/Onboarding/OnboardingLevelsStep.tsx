import { Badge, Button } from '../../components/ui';
import type { CEFRLevel } from '../../types/api';
import { OnboardingStep } from './OnboardingStep';
import { useOnboardingFlow } from './useOnboardingFlow';
import styles from './OnboardingPage.module.css';

const CEFR_LEVELS: CEFRLevel[] = ['A1', 'A2', 'B1', 'B2', 'C1', 'C2'];

const LEVEL_OPTIONS: { id: CEFRLevel; label: string; note: string }[] = [
    { id: 'A1', label: 'A1 — начинаю', note: 'Понимаю отдельные слова' },
    { id: 'A2', label: 'A2 — базовый', note: 'О знакомых темах, простые ответы' },
    { id: 'B1', label: 'B1 — продолжаю', note: 'Поддерживаю разговор' },
    { id: 'B2', label: 'B2 — уверенный', note: 'Работа/путешествия комфортно' },
    { id: 'C1', label: 'C1 — продвинутый', note: 'Почти носитель' },
    { id: 'C2', label: 'C2 — свободный', note: 'Близко к носителю' },
];

export const OnboardingLevelsStep = () => {
    const { goNext, goPrev, form, updateField, submitting } = useOnboardingFlow();

    const handleSelectCurrent = (level: CEFRLevel) => {
        updateField('currentLevel', level);
        const currentIndex = CEFR_LEVELS.indexOf(level);
        const targetIndex = CEFR_LEVELS.indexOf(form.targetLevel);
        if (targetIndex < currentIndex) {
            updateField('targetLevel', level);
        }
    };

    const handleSelectTarget = (level: CEFRLevel) => {
        updateField('targetLevel', level);
    };

    const targetLevels = LEVEL_OPTIONS.filter(
        (option) => CEFR_LEVELS.indexOf(option.id) >= CEFR_LEVELS.indexOf(form.currentLevel),
    );

    return (
        <OnboardingStep
            title="Какой у вас сейчас уровень?"
            description="Подберём стартовые блоки и количество новых слов в день."
            actions={
                <>
                    <Button variant="secondary" onClick={goPrev} disabled={submitting}>
                        Назад
                    </Button>
                    <Button onClick={goNext} disabled={submitting}>
                        Дальше
                    </Button>
                </>
            }
        >
            <div className={styles.levelsGrid}>
                <div className={styles.levelGroup}>
                    <div className={styles.sectionHeader}>
                        <span>Текущий уровень</span>
                        <Badge variant="info">Честно оцениваем старт</Badge>
                    </div>
                    <div className={styles.options}>
                        {LEVEL_OPTIONS.map((level) => (
                            <Button
                                key={level.id}
                                variant={form.currentLevel === level.id ? 'secondary' : 'ghost'}
                                className={styles.optionButton}
                                fullWidth
                                onClick={() => handleSelectCurrent(level.id)}
                                disabled={submitting}
                            >
                                <span>
                                    {level.label} <Badge variant="info">{level.note}</Badge>
                                </span>
                                {form.currentLevel === level.id && <span aria-hidden>✓</span>}
                            </Button>
                        ))}
                    </div>
                </div>

                <div className={styles.levelGroup}>
                    <div className={styles.sectionHeader}>
                        <span>Целевой уровень</span>
                        <Badge variant="warning">Подберём шаги</Badge>
                    </div>
                    <div className={styles.options}>
                        {targetLevels.map((level) => (
                            <Button
                                key={level.id}
                                variant={form.targetLevel === level.id ? 'secondary' : 'ghost'}
                                className={styles.optionButton}
                                fullWidth
                                onClick={() => handleSelectTarget(level.id)}
                                disabled={submitting}
                            >
                                <span>{level.label}</span>
                                {form.targetLevel === level.id && <span aria-hidden>✓</span>}
                            </Button>
                        ))}
                    </div>
                </div>
            </div>
        </OnboardingStep>
    );
};
