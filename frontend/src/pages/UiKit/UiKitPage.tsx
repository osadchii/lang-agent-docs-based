import { useMemo, useState } from 'react';
import {
    Badge,
    Button,
    Card,
    EmptyState,
    Input,
    Modal,
    Progress,
    Skeleton,
    Tabs,
    Textarea,
    useToast,
} from '../../components/ui';
import { useTheme } from '../../styles/theme';
import styles from './UiKitPage.module.css';

export const UiKitPage = () => {
    const [activeTab, setActiveTab] = useState('overview');
    const [progress, setProgress] = useState(42);
    const [isModalOpen, setIsModalOpen] = useState(false);
    const [isSheetOpen, setIsSheetOpen] = useState(false);
    const { success, error, info, warning } = useToast();
    const { mode, setMode } = useTheme();

    const tabs = useMemo(
        () => [
            { id: 'overview', label: 'Общее', icon: '✨' },
            { id: 'practice', label: 'Практика', icon: '🧠' },
            { id: 'profile', label: 'Профиль', icon: '👤' },
        ],
        [],
    );

    return (
        <div className={styles.page}>
            <div className={styles.headline}>
                <div>
                    <div className={styles.title}>UI Kit Mini App</div>
                    <div className={styles.muted}>
                        Базовые строительные блоки мини-приложения с поддержкой тем Telegram.
                    </div>
                </div>
                <div className={styles.row}>
                    <Badge variant="info">Тема: {mode}</Badge>
                    <Button
                        variant="secondary"
                        size="sm"
                        onClick={() => setMode(mode === 'dark' ? 'light' : 'dark')}
                    >
                        Переключить тему
                    </Button>
                </div>
            </div>

            <Card title="Кнопки и бейджи" subtitle="Сценарии действий и статусы">
                <div className={styles.grid}>
                    <div className={styles.stack}>
                        <div className={styles.sectionTitle}>Главные действия</div>
                        <div className={styles.row}>
                            <Button>Primary</Button>
                            <Button variant="secondary">Secondary</Button>
                            <Button variant="ghost">Ghost</Button>
                            <Button variant="mono" icon="⚙">
                                Icon left
                            </Button>
                            <Button variant="danger" icon="!">
                                Danger
                            </Button>
                        </div>
                    </div>
                    <div className={styles.stack}>
                        <div className={styles.sectionTitle}>Состояния</div>
                        <div className={styles.row}>
                            <Button loading>Загрузка</Button>
                            <Button disabled variant="secondary">
                                Disabled
                            </Button>
                            <Button size="sm" icon="➕">
                                Маленькая
                            </Button>
                        </div>
                        <div className={styles.row}>
                            <Badge>Neutral</Badge>
                            <Badge variant="success">Success</Badge>
                            <Badge variant="warning">Warning</Badge>
                            <Badge variant="error">Error</Badge>
                            <Badge variant="info">Info</Badge>
                        </div>
                    </div>
                </div>
            </Card>

            <Card title="Поля ввода" subtitle="Input, Textarea, состояния ошибок" elevated>
                <div className={styles.grid}>
                    <Input label="Email" placeholder="you@example.com" leftIcon="✉" />
                    <Input
                        label="Код"
                        placeholder="Введите код"
                        error="Неверный код"
                        rightIcon="⚡"
                    />
                    <Textarea
                        label="Цель занятий"
                        placeholder="Расскажите, чего хотите достичь..."
                        hint="Можно менять в любое время"
                    />
                </div>
            </Card>

            <Card title="Табы и прогресс" subtitle="Навигация и статусы процесса" gradient>
                <div className={styles.stack}>
                    <Tabs tabs={tabs} activeTab={activeTab} onChange={setActiveTab} />
                    <div className={styles.row}>
                        <Progress
                            value={progress}
                            label="Прогресс по теме"
                            showValue
                            className={styles.stack}
                        />
                        <Progress type="spinner" label="Подготовка" />
                    </div>
                    <div className={styles.row}>
                        <Button size="sm" onClick={() => setProgress((p) => Math.min(100, p + 15))}>
                            +15%
                        </Button>
                        <Button
                            size="sm"
                            variant="secondary"
                            onClick={() => setProgress((p) => Math.max(0, p - 15))}
                        >
                            -15%
                        </Button>
                        <Button size="sm" variant="ghost" onClick={() => setProgress(42)}>
                            Сбросить
                        </Button>
                    </div>
                </div>
            </Card>

            <Card title="Состояния загрузки" subtitle="Скелетоны и пустые экраны">
                <div className={styles.grid}>
                    <div className={styles.stack}>
                        <div className={styles.sectionTitle}>Skeleton</div>
                        <Skeleton variant="text" width="60%" />
                        <Skeleton height={18} />
                        <Skeleton width="40%" />
                        <Skeleton variant="rect" height={120} />
                    </div>
                    <EmptyState
                        icon="🌌"
                        title="Нет карточек"
                        description="Добавьте первую карточку, чтобы начать тренировку. Мы сохраним прогресс и подберем задания."
                        actions={
                            <Button
                                size="sm"
                                onClick={() => info('Добавление', 'Заглушка действия')}
                            >
                                Добавить
                            </Button>
                        }
                    />
                </div>
            </Card>

            <Card title="Модальные окна и тосты" subtitle="Диалоги, bottom sheet, уведомления">
                <div className={styles.row}>
                    <Button onClick={() => setIsModalOpen(true)}>Диалог</Button>
                    <Button variant="secondary" onClick={() => setIsSheetOpen(true)}>
                        Bottom sheet
                    </Button>
                    <Button variant="ghost" onClick={() => success('Успех', 'Действие выполнено')}>
                        Toast success
                    </Button>
                    <Button variant="ghost" onClick={() => warning('Внимание', 'Проверьте данные')}>
                        Toast warning
                    </Button>
                    <Button variant="ghost" onClick={() => error('Ошибка', 'Что-то пошло не так')}>
                        Toast error
                    </Button>
                </div>
            </Card>

            <Modal
                open={isModalOpen}
                onClose={() => setIsModalOpen(false)}
                title="Модальное окно"
                subtitle="Используйте для подтверждений и настроек"
                footer={
                    <>
                        <Button variant="ghost" onClick={() => setIsModalOpen(false)}>
                            Отмена
                        </Button>
                        <Button onClick={() => setIsModalOpen(false)}>Сохранить</Button>
                    </>
                }
            >
                <p>Здесь можно разместить формы, подсказки или превью данных.</p>
            </Modal>

            <Modal
                open={isSheetOpen}
                onClose={() => setIsSheetOpen(false)}
                title="Выбор действия"
                type="bottomSheet"
                closeOnBackdrop
            >
                <div className={styles.stack}>
                    <Button fullWidth>Добавить карточку</Button>
                    <Button fullWidth variant="secondary">
                        Создать дек
                    </Button>
                    <Button fullWidth variant="ghost" onClick={() => setIsSheetOpen(false)}>
                        Закрыть
                    </Button>
                </div>
            </Modal>
        </div>
    );
};
