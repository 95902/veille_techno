const dateFormat = new Intl.DateTimeFormat('fr-FR', { dateStyle: 'long' });

export function formatArticleDate(value: string | null): string {
    return value ? dateFormat.format(new Date(value)) : '';
}

/** The summary is stored one sentence per line. */
export function summaryLines(summary: string | null): string[] {
    return (summary ?? '')
        .split('\n')
        .map((line) => line.trim())
        .filter((line) => line !== '');
}
