import { useQueryClient } from '@tanstack/react-query';
import type { PropsWithChildren } from 'react';
import { useCallback, useMemo, useState } from 'react';
import { Outlet, useLocation, useNavigate } from 'react-router-dom';
import { createProfile, activateProfile } from '../../../api/profiles';
import { queryKeys } from '../../../api/queryKeys';
import { getErrorMessage } from '../../../api/errors';
import type { CEFRLevel, LanguageProfile, LanguageProfileCreatePayload } from '../../../types/api';
import { useToast } from '../../ui';
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
    complete: () => Promise<void>;
    submitting: boolean;
    submitError: string | null;
    clearError: () => void;
    form: OnboardingFormState;
    updateField: <K extends keyof OnboardingFormState>(
        key: K,
        value: OnboardingFormState[K],
    ) => void;
    toggleGoal: (goal: string) => void;
}

export interface OnboardingFormState {
    language: string;
    currentLevel: CEFRLevel;
    targetLevel: CEFRLevel;
    goals: string[];
    interfaceLanguage: string;
}

const steps: OnboardingStep[] = [
    {
        id: 'welcome',
        path: '/onboarding/welcome',
        title: 'Приветствие',
        description: 'Коротко познакомимся и настроим аккаунт',
    },
    {
        id: 'language',
        path: '/onboarding/language',
        title: 'Язык',
        description: 'Выберите язык, который хотите прокачать первым',
    },
    {
        id: 'levels',
        path: '/onboarding/levels',
        title: 'Уровень',
        description: 'Уточните старт и цель, чтобы подобрать нагрузку',
    },
    {
        id: 'goals',
        path: '/onboarding/goals',
        title: 'Цели',
        description: 'Выберите, на чём сфокусироваться в первую очередь',
    },
    {
        id: 'interface',
        path: '/onboarding/interface',
        title: 'Интерфейс',
        description: 'Выберите язык интерфейса и режим подсказок',
    },
];

const DEFAULT_FORM_STATE: OnboardingFormState = {
    language: 'en',
    currentLevel: 'B1',
    targetLevel: 'B2',
    goals: ['speaking'],
    interfaceLanguage: 'ru',
};

const getActiveIndex = (pathname: string) => {
    const found = steps.findIndex((step) => pathname.includes(step.id));
    return found >= 0 ? found : 0;
};

export const OnboardingLayout = ({ children }: PropsWithChildren) => {
    const location = useLocation();
    const navigate = useNavigate();
    const queryClient = useQueryClient();
    const { markComplete, refreshStatus } = useOnboarding();
    const { success: showSuccess, error: showError } = useToast();

    const [formState, setFormState] = useState<OnboardingFormState>(DEFAULT_FORM_STATE);
    const [submitting, setSubmitting] = useState(false);
    const [submitError, setSubmitError] = useState<string | null>(null);

    const activeIndex = getActiveIndex(location.pathname);
    const atFirstStep = activeIndex === 0;
    const atLastStep = activeIndex === steps.length - 1;
    const progress = ((activeIndex + 1) / steps.length) * 100;

    const clearError = useCallback(() => setSubmitError(null), []);

    const updateField = useCallback(
        <K extends keyof OnboardingFormState>(key: K, value: OnboardingFormState[K]) => {
            clearError();
            setFormState((prev) => ({ ...prev, [key]: value }));
        },
        [clearError],
    );

    const toggleGoal = useCallback(
        (goal: string) => {
            clearError();
            setFormState((prev) => {
                const exists = prev.goals.includes(goal);
                const goals = exists
                    ? prev.goals.filter((item) => item !== goal)
                    : [...prev.goals, goal];
                return { ...prev, goals };
            });
        },
        [clearError],
    );

    const persistProfileCache = useCallback(
        (profile: LanguageProfile) => {
            queryClient.setQueryData<LanguageProfile[]>(queryKeys.profiles, (current) => {
                if (!current || current.length === 0) {
                    return [profile];
                }
                const updated = current.map((item) => ({
                    ...item,
                    is_active: item.id === profile.id,
                }));
                if (!updated.some((item) => item.id === profile.id)) {
                    updated.unshift(profile);
                }
                return updated;
            });
        },
        [queryClient],
    );

    const complete = useCallback(async () => {
        if (submitting) {
            return;
        }

        const cachedProfiles = queryClient.getQueryData<LanguageProfile[]>(queryKeys.profiles);
        const alreadyActive = cachedProfiles?.find((profile) => profile.is_active);
        if (alreadyActive) {
            markComplete();
            navigate('/', { replace: true });
            return;
        }

        const payload: LanguageProfileCreatePayload = {
            language: formState.language,
            current_level: formState.currentLevel,
            target_level: formState.targetLevel,
            goals: formState.goals.length > 0 ? formState.goals : ['speaking'],
            interface_language: formState.interfaceLanguage,
        };

        setSubmitting(true);
        clearError();

        try {
            let profile = await createProfile(payload);
            if (!profile.is_active) {
                profile = await activateProfile(profile.id);
            }

            persistProfileCache(profile);
            markComplete();
            await refreshStatus();
            showSuccess('Профиль готов', 'Можно начинать практику.');
            navigate('/', { replace: true });
        } catch (error) {
            const hasProfile = await refreshStatus();
            if (hasProfile) {
                showSuccess('Профиль уже активен', 'Продолжаем с текущими настройками.');
                navigate('/', { replace: true });
                return;
            }

            const message = getErrorMessage(error, 'Не удалось завершить онбординг.');
            setSubmitError(message);
            showError(message);
        } finally {
            setSubmitting(false);
        }
    }, [
        clearError,
        formState.currentLevel,
        formState.goals,
        formState.interfaceLanguage,
        formState.language,
        formState.targetLevel,
        markComplete,
        navigate,
        persistProfileCache,
        queryClient,
        refreshStatus,
        showError,
        showSuccess,
        submitting,
    ]);

    const goNext = useCallback(() => {
        if (atLastStep) {
            void complete();
            return;
        }
        navigate(steps[activeIndex + 1].path);
    }, [activeIndex, atLastStep, complete, navigate]);

    const goPrev = useCallback(() => {
        if (atFirstStep) {
            return;
        }
        navigate(steps[activeIndex - 1].path);
    }, [atFirstStep, activeIndex, navigate]);

    const contextValue = useMemo(
        () =>
            ({
                steps,
                activeIndex,
                goNext,
                goPrev,
                complete,
                submitting,
                submitError,
                clearError,
                form: formState,
                updateField,
                toggleGoal,
            }) satisfies OnboardingFlowContext,
        [
            activeIndex,
            clearError,
            complete,
            formState,
            goNext,
            goPrev,
            submitError,
            submitting,
            updateField,
            toggleGoal,
        ],
    );

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
                    <button
                        type="button"
                        className={styles.skip}
                        onClick={() => void complete()}
                        disabled={submitting}
                    >
                        Пропустить
                    </button>
                </div>
            </div>

            <div className={styles.body}>
                <Outlet context={contextValue} />
                {children}
            </div>
        </div>
    );
};
