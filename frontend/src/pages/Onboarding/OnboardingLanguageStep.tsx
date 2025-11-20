import { Badge, Button } from '../../components/ui';
import { OnboardingStep } from './OnboardingStep';
import { useOnboardingFlow } from './useOnboardingFlow';
import styles from './OnboardingPage.module.css';

const languages = [
    { id: 'en', label: 'Английский' },
    { id: 'es', label: 'Испанский' },
    { id: 'de', label: 'Немецкий' },
    { id: 'fr', label: 'Французский' },
];

export const OnboardingLanguageStep = () => {
    const { goNext, form, updateField, submitting } = useOnboardingFlow();
    const selected = form.language;

    return (
        <OnboardingStep
            title="Какой язык качаем первым?"
            description="Можно добавить дополнительные профили позже. Синхронизируем с ботом автоматически."
            actions={
                <>
                    <Badge variant="info">Можно поменять позже</Badge>
                    <Button onClick={goNext} disabled={submitting}>
                        Дальше
                    </Button>
                </>
            }
        >
            <div className={styles.options}>
                {languages.map((language) => (
                    <Button
                        key={language.id}
                        variant={selected === language.id ? 'secondary' : 'ghost'}
                        className={styles.optionButton}
                        fullWidth
                        onClick={() => updateField('language', language.id)}
                        disabled={submitting}
                    >
                        {language.label}
                        {selected === language.id && <span aria-hidden>✓</span>}
                    </Button>
                ))}
            </div>
        </OnboardingStep>
    );
};
