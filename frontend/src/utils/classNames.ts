export type ClassValue = string | null | undefined | false | Record<string, boolean>;

export const classNames = (...values: ClassValue[]): string => {
    const parts: string[] = [];

    values.forEach((value) => {
        if (!value) {
            return;
        }

        if (typeof value === 'string') {
            parts.push(value);
            return;
        }

        Object.entries(value).forEach(([key, active]) => {
            if (active) {
                parts.push(key);
            }
        });
    });

    return parts.join(' ');
};
