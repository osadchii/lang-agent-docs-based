import type { PropsWithChildren } from 'react';
import { Outlet, useLocation, useNavigate } from 'react-router-dom';
import { Header } from '../Header/Header';
import { useOnboarding } from '../../../providers/OnboardingProvider';
import styles from './OnboardingLayout.module.css';

export interface OnboardingStep {
    id: string;
    path: string;
    title: string;
    description: string;
}

export interface OnboardingFlowContext {
    steps: OnboardingStep[];
    activeIndex: number;
    goNext: () => void;
    goPrev: () => void;
    complete: () => void;
}

const steps: OnboardingStep[] = [
    {
        id: 'language',
        path: '/onboarding/language',
        title: 'Язык',
        description: 'Выберите язык, который хотите прокачать первым',
    },
    {
        id: 'current',
        path: '/onboarding/current',
        title: 'Текущий уровень',
        description: 'Поможем подобрать упражнения под ваш уровень',
    },
    {
        id: 'target',
        path: '/onboarding/target',
        title: 'Цель',
        description: 'Что для вас важнее: говорение, грамматика или словарный запас',
    },
    {
        id: 'goal',
        path: '/onboarding/goal',
        title: 'Режим',
        description: 'Настройте темп занятий и тип практики',
    },
    {
        id: 'interface',
        path: '/onboarding/interface',
        title: 'Интерфейс',
        description: 'Выберите язык интерфейса и режим подсказок',
    },
];

const getActiveIndex = (pathname: string) => {
    const found = steps.findIndex((step) => pathname.includes(step.id));
    return found >= 0 ? found : 0;
};

export const OnboardingLayout = ({ children }: PropsWithChildren) => {
    const location = useLocation();
    const navigate = useNavigate();
    const { markComplete } = useOnboarding();

    const activeIndex = getActiveIndex(location.pathname);
    const atFirstStep = activeIndex === 0;
    const atLastStep = activeIndex === steps.length - 1;
    const progress = ((activeIndex + 1) / steps.length) * 100;

    const goNext = () => {
        if (atLastStep) {
            complete();
            return;
        }
        navigate(steps[activeIndex + 1].path);
    };

    const goPrev = () => {
        if (atFirstStep) {
            return;
        }
        navigate(steps[activeIndex - 1].path);
    };

    const complete = () => {
        markComplete();
        navigate('/', { replace: true });
    };

    return (
        <div className={styles.layout}>
            <Header
                title="Онбординг"
                subtitle="Подготовим ваше обучение за минуту"
                showBack={!atFirstStep}
                onBack={atFirstStep ? undefined : goPrev}
            />

            <div className={styles.progress}>
                <div className={styles.progressBar}>
                    <div className={styles.progressFill} style={{ width: `${progress}%` }} />
                </div>
                <div className={styles.progressMeta}>
                    <span>
                        Шаг {activeIndex + 1} из {steps.length}
                    </span>
                    <button type="button" className={styles.skip} onClick={complete}>
                        Пропустить
                    </button>
                </div>
            </div>

            <div className={styles.body}>
                <Outlet
                    context={
                        {
                            steps,
                            activeIndex,
                            goNext,
                            goPrev,
                            complete,
                        } satisfies OnboardingFlowContext
                    }
                />
                {children}
            </div>
        </div>
    );
};
