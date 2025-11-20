import { Navigate, createBrowserRouter } from 'react-router-dom';
import { AppFrame } from '../components/layout/AppFrame/AppFrame';
import { OnboardingLayout } from '../components/layout/OnboardingLayout/OnboardingLayout';
import { PracticeLayout } from '../components/layout/PracticeLayout/PracticeLayout';
import { RootLayout } from '../components/layout/RootLayout/RootLayout';
import { AuthGuard, OnboardingCompletedRedirect } from './guards';
import type { AppRouteHandle } from './types';
import { ErrorPage } from '../pages/Error/ErrorPage';
import { GroupsPage } from '../pages/Groups/GroupsPage';
import { HomePage } from '../pages/Home/HomePage';
import { OnboardingGoalsStep } from '../pages/Onboarding/OnboardingGoalsStep';
import { OnboardingInterfaceStep } from '../pages/Onboarding/OnboardingInterfaceStep';
import { OnboardingLanguageStep } from '../pages/Onboarding/OnboardingLanguageStep';
import { OnboardingLevelsStep } from '../pages/Onboarding/OnboardingLevelsStep';
import { OnboardingWelcomeStep } from '../pages/Onboarding/OnboardingWelcomeStep';
import { CardSessionPage } from '../pages/Practice/CardSessionPage';
import { CardsPage } from '../pages/Practice/CardsPage';
import { ExerciseSessionPage } from '../pages/Practice/ExerciseSessionPage';
import { ExercisesPage } from '../pages/Practice/ExercisesPage';
import { ProfilePage } from '../pages/Profile/ProfilePage';
import { UiKitPage } from '../pages/UiKit/UiKitPage';

export const router = createBrowserRouter([
    {
        path: '/',
        element: <AppFrame />,
        errorElement: <ErrorPage />,
        children: [
            {
                element: <AuthGuard />,
                children: [
                    {
                        element: <RootLayout />,
                        children: [
                            { index: true, element: <HomePage /> },
                            {
                                path: 'practice',
                                element: (
                                    <PracticeLayout
                                        title="Практика"
                                        subtitle="Карточки и упражнения"
                                        tabs={[
                                            { id: 'cards', label: 'Карточки', icon: '🃏' },
                                            { id: 'exercises', label: 'Упражнения', icon: '🧠' },
                                        ]}
                                    />
                                ),
                                children: [
                                    {
                                        index: true,
                                        element: <Navigate to="/practice/cards" replace />,
                                    },
                                    { path: 'cards', element: <CardsPage /> },
                                    { path: 'exercises', element: <ExercisesPage /> },
                                    {
                                        path: 'cards/study',
                                        element: (
                                            <PracticeLayout
                                                title="Сессия карточек"
                                                subtitle="Полноэкранный режим без BottomNav"
                                                backTo="/practice/cards"
                                                fullHeight
                                            >
                                                <CardSessionPage />
                                            </PracticeLayout>
                                        ),
                                        handle: { hideBottomNav: true } satisfies AppRouteHandle,
                                    },
                                    {
                                        path: 'exercises/session',
                                        element: (
                                            <PracticeLayout
                                                title="Сессия упражнений"
                                                subtitle="Отвечайте, мы дадим фидбек"
                                                backTo="/practice/exercises"
                                                fullHeight
                                            >
                                                <ExerciseSessionPage />
                                            </PracticeLayout>
                                        ),
                                        handle: { hideBottomNav: true } satisfies AppRouteHandle,
                                    },
                                ],
                            },
                            { path: 'groups', element: <GroupsPage /> },
                            { path: 'profile', element: <ProfilePage /> },
                            {
                                path: 'ui-kit',
                                element: <UiKitPage />,
                                handle: { hideBottomNav: true } satisfies AppRouteHandle,
                            },
                        ],
                    },
                    {
                        path: 'onboarding',
                        element: (
                            <OnboardingCompletedRedirect>
                                <OnboardingLayout />
                            </OnboardingCompletedRedirect>
                        ),
                        handle: {
                            hideBottomNav: true,
                            hideBackButton: true,
                        } satisfies AppRouteHandle,
                        children: [
                            {
                                index: true,
                                element: <Navigate to="/onboarding/welcome" replace />,
                            },
                            { path: 'welcome', element: <OnboardingWelcomeStep /> },
                            { path: 'language', element: <OnboardingLanguageStep /> },
                            { path: 'levels', element: <OnboardingLevelsStep /> },
                            { path: 'goals', element: <OnboardingGoalsStep /> },
                            { path: 'interface', element: <OnboardingInterfaceStep /> },
                        ],
                    },
                    { path: 'error', element: <ErrorPage /> },
                ],
            },
        ],
    },
    { path: '*', element: <ErrorPage /> },
]);
