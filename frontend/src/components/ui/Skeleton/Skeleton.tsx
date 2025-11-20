import type { CSSProperties, HTMLAttributes } from 'react';
import { classNames } from '../../../utils/classNames';
import styles from './Skeleton.module.css';

type SkeletonVariant = 'text' | 'rect' | 'circle';

export interface SkeletonProps extends HTMLAttributes<HTMLDivElement> {
    width?: number | string;
    height?: number | string;
    variant?: SkeletonVariant;
}

export const Skeleton = ({
    width,
    height,
    variant = 'rect',
    className,
    style,
    ...rest
}: SkeletonProps) => {
    const customStyle: CSSProperties = {
        width,
        height,
        ...style,
    };

    return (
        <div
            className={classNames(
                styles.skeleton,
                styles[`variant${variant[0].toUpperCase()}${variant.slice(1)}`],
                className,
            )}
            style={customStyle}
            aria-hidden
            {...rest}
        />
    );
};
