import { Outlet, ScrollRestoration } from 'react-router-dom';
import { BackButtonSync } from '../../navigation/BackButtonSync';
import styles from './AppFrame.module.css';

export const AppFrame = () => {
    return (
        <div className={styles.frame}>
            <BackButtonSync />
            <Outlet />
            <ScrollRestoration />
        </div>
    );
};
