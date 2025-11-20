/**
 * React Router configuration
 * Defines all routes for the Mini App
 */

import { createBrowserRouter } from 'react-router-dom';
import { HomePage } from '../pages/Home/HomePage';
import { ErrorPage } from '../pages/Error/ErrorPage';
import { UiKitPage } from '../pages/UiKit/UiKitPage';

export const router = createBrowserRouter([
    {
        path: '/',
        element: <HomePage />,
        errorElement: <ErrorPage />,
    },
    {
        path: '/error',
        element: <ErrorPage />,
    },
    {
        path: '/ui-kit',
        element: <UiKitPage />,
    },
    {
        path: '*',
        element: <ErrorPage />,
    },
]);
