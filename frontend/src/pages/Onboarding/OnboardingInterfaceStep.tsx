import { useState } from 'react';
import { Badge, Button } from '../../components/ui';
import { OnboardingStep } from './OnboardingStep';
import { useOnboardingFlow } from './useOnboardingFlow';
import styles from './OnboardingPage.module.css';

const interfaces = [
    { id: 'ru', label: 'Русский', note: 'Подсказки и примеры на русском' },
    { id: 'en', label: 'English', note: 'Интерфейс и хинты на английском' },
];

export const OnboardingInterfaceStep = () => {
    const { complete } = useOnboardingFlow();
    const [selected, setSelected] = useState<string>('ru');

    return (
        <OnboardingStep
            title="Настроим интерфейс"
            description="Синхронизируем тему Telegram и включим подсказки для первых шагов."
            actions={
                <>
                    <Badge variant="success">Всегда можно поменять в настройках</Badge>
                    <Button onClick={complete}>Завершить</Button>
                </>
            }
        >
            <div className={styles.options}>
                {interfaces.map((item) => (
                    <Button
                        key={item.id}
                        variant={selected === item.id ? 'secondary' : 'ghost'}
                        className={styles.optionButton}
                        fullWidth
                        onClick={() => setSelected(item.id)}
                    >
                        <span>
                            {item.label} <Badge variant="info">{item.note}</Badge>
                        </span>
                        {selected === item.id && <span aria-hidden>✓</span>}
                    </Button>
                ))}
            </div>
        </OnboardingStep>
    );
};
