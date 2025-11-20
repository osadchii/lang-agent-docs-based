import type { PropsWithChildren, ReactNode } from 'react';
import styles from './OnboardingPage.module.css';

interface OnboardingStepProps extends PropsWithChildren {
    title: string;
    description: string;
    actions?: ReactNode;
}

export const OnboardingStep = ({ title, description, children, actions }: OnboardingStepProps) => {
    return (
        <div className={styles.card}>
            <div className={styles.title}>{title}</div>
            <div className={styles.description}>{description}</div>
            {children}
            {actions && <div className={styles.footActions}>{actions}</div>}
        </div>
    );
};
