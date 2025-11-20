import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import './styles/globals.css';
import './index.css';
import { ToastProvider } from './components/ui/Toast';
import { AppErrorBoundary } from './components/state/AppErrorBoundary';
import { ThemeProvider } from './styles/theme';
import { ApiProvider } from './providers/ApiProvider';
import { AuthProvider } from './providers/AuthProvider';
import { OnboardingProvider } from './providers/OnboardingProvider';
import App from './App.tsx';

createRoot(document.getElementById('root')!).render(
    <StrictMode>
        <ApiProvider>
            <AppErrorBoundary>
                <ThemeProvider>
                    <AuthProvider>
                        <OnboardingProvider>
                            <ToastProvider>
                                <App />
                            </ToastProvider>
                        </OnboardingProvider>
                    </AuthProvider>
                </ThemeProvider>
            </AppErrorBoundary>
        </ApiProvider>
    </StrictMode>,
);
