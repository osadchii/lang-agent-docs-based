import { useOutletContext } from 'react-router-dom';
import type { OnboardingFlowContext } from '../../components/layout/OnboardingLayout/OnboardingLayout';

export const useOnboardingFlow = () => useOutletContext<OnboardingFlowContext>();
