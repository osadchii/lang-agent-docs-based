import { Badge, Button, Card } from '../../components/ui';
import { Header } from '../../components/layout/Header/Header';
import { useAuthContext } from '../../providers/AuthProvider';
import { useOnboarding } from '../../providers/OnboardingProvider';
import styles from './ProfilePage.module.css';

export const ProfilePage = () => {
    const { user } = useAuthContext();
    const { reset } = useOnboarding();

    return (
        <div className={styles.screen}>
            <Header
                title="Профиль"
                subtitle="Синхронизирован с Telegram. Управляйте настройками обучения."
            />

            <Card elevated gradient title={user?.first_name ?? 'Пользователь'}>
                <div className={styles.row}>
                    <Badge variant="info">Telegram ID: {user?.telegram_id ?? '—'}</Badge>
                    <Badge variant={user?.is_premium ? 'success' : 'warning'}>
                        {user?.is_premium ? 'Premium' : 'Бесплатный'}
                    </Badge>
                </div>
                <div className={styles.muted}>
                    Мы учитываем ваши профили, стрик и прогресс по карточкам в боте и Mini App.
                </div>
                <div className={styles.row}>
                    <Button size="sm" variant="secondary">
                        Настройки
                    </Button>
                    <Button size="sm" variant="ghost" onClick={reset}>
                        Сбросить онбординг
                    </Button>
                </div>
            </Card>

            <div className={styles.cardGrid}>
                <Card title="Способы улучшить опыт" subtitle="Идеи по навигации и haptics">
                    <ul className={styles.muted}>
                        <li>Используем BackButton Telegram на внутренних экранах.</li>
                        <li>MainButton активируется для сессий карточек и упражнений.</li>
                        <li>Haptics для вкладок, рейтингов и системных действий.</li>
                    </ul>
                </Card>
            </div>
        </div>
    );
};
