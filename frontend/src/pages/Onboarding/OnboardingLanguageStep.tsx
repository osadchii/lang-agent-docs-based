import { useState } from 'react';
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
    const { goNext } = useOnboardingFlow();
    const [selected, setSelected] = useState<string>('en');

    return (
        <OnboardingStep
            title="Какой язык качаем первым?"
            description="Можно добавить дополнительные профили позже. Синхронизируем с ботом автоматически."
            actions={
                <>
                    <Badge variant="info">Можно поменять позже</Badge>
                    <Button onClick={goNext}>Дальше</Button>
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
                        onClick={() => setSelected(language.id)}
                    >
                        {language.label}
                        {selected === language.id && <span aria-hidden>✓</span>}
                    </Button>
                ))}
            </div>
        </OnboardingStep>
    );
};
