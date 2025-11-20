import { Badge, Button } from '../../components/ui';
import { OnboardingStep } from './OnboardingStep';
import { useOnboardingFlow } from './useOnboardingFlow';
import styles from './OnboardingPage.module.css';

const interfaces = [
    { id: 'ru', label: 'Русский', note: 'Подсказки и примеры на русском' },
    { id: 'en', label: 'English', note: 'Интерфейс и хинты на английском' },
];

const languageLabels: Record<string, string> = {
    en: 'Английский',
    es: 'Испанский',
    de: 'Немецкий',
    fr: 'Французский',
};

const goalLabels: Record<string, string> = {
    speaking: 'Говорение',
    vocabulary: 'Словарь',
    grammar: 'Грамматика',
};

export const OnboardingInterfaceStep = () => {
    const { form, updateField, complete, goPrev, submitting, submitError } = useOnboardingFlow();

    return (
        <OnboardingStep
            title="Настроим интерфейс"
            description="Синхронизируем тему Telegram и включим подсказки для первых шагов."
            actions={
                <>
                    <Button variant="secondary" onClick={goPrev} disabled={submitting}>
                        Назад
                    </Button>
                    <Button onClick={() => void complete()} disabled={submitting}>
                        {submitting ? 'Создаём профиль...' : 'Завершить'}
                    </Button>
                </>
            }
        >
            <div className={styles.options}>
                {interfaces.map((item) => (
                    <Button
                        key={item.id}
                        variant={form.interfaceLanguage === item.id ? 'secondary' : 'ghost'}
                        className={styles.optionButton}
                        fullWidth
                        onClick={() => updateField('interfaceLanguage', item.id)}
                        disabled={submitting}
                    >
                        <span>
                            {item.label} <Badge variant="info">{item.note}</Badge>
                        </span>
                        {form.interfaceLanguage === item.id && <span aria-hidden>✓</span>}
                    </Button>
                ))}
            </div>

            <div className={styles.summaryCard}>
                <div className={styles.sectionHeader}>
                    <span>Проверим настройки</span>
                    <Badge variant="success">Можно изменить позже</Badge>
                </div>
                <dl className={styles.summaryList}>
                    <div>
                        <dt>Язык изучения</dt>
                        <dd>{languageLabels[form.language] ?? form.language.toUpperCase()}</dd>
                    </div>
                    <div>
                        <dt>Уровень</dt>
                        <dd>
                            {form.currentLevel} → {form.targetLevel}
                        </dd>
                    </div>
                    <div>
                        <dt>Цели</dt>
                        <dd>
                            {form.goals.length === 0
                                ? 'Не выбраны'
                                : form.goals.map((goal) => goalLabels[goal] ?? goal).join(', ')}
                        </dd>
                    </div>
                    <div>
                        <dt>Интерфейс</dt>
                        <dd>
                            {interfaces.find((item) => item.id === form.interfaceLanguage)?.label ??
                                form.interfaceLanguage}
                        </dd>
                    </div>
                </dl>
            </div>

            {submitError && <div className={styles.error}>{submitError}</div>}
        </OnboardingStep>
    );
};
