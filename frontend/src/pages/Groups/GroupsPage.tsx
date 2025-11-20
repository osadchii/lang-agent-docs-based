import { Badge, Button, Card } from '../../components/ui';
import { Header } from '../../components/layout/Header/Header';
import styles from './GroupsPage.module.css';

const mockGroups = [
    { id: 'club', name: 'Speaking Club', members: 18, unread: 3 },
    { id: 'team', name: 'Work English', members: 9, unread: 0 },
];

export const GroupsPage = () => {
    return (
        <div className={styles.screen}>
            <Header title="Группы" subtitle="Совместные тренировки и шаринг материалов" />
            <div className={styles.headerRow}>
                <div className={styles.title}>Мои группы</div>
                <Button size="sm" variant="secondary">
                    Создать
                </Button>
            </div>
            <div className={styles.grid}>
                {mockGroups.map((group) => (
                    <Card
                        key={group.id}
                        elevated
                        gradient
                        title={group.name}
                        subtitle={`${group.members} участников`}
                        footer={
                            <Badge variant={group.unread > 0 ? 'warning' : 'info'}>
                                {group.unread > 0
                                    ? `Непрочитанных: ${group.unread}`
                                    : 'Без новых сообщений'}
                            </Badge>
                        }
                    >
                        <div className={styles.muted}>Материалы, карточки и общий прогресс.</div>
                    </Card>
                ))}
            </div>
        </div>
    );
};
