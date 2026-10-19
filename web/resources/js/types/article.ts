export type ArticleCategory = {
    name: string;
    slug: string;
};

export type ArticleSummary = {
    id: number;
    title_fr: string;
    summary: string | null;
    published_at: string | null;
    source: string | null;
    category: ArticleCategory | null;
};

export type ArticleDetail = ArticleSummary & {
    title: string;
    url: string;
};

export type ArticleFilters = {
    q: string;
    categorie: string;
};

export type Paginated<T> = {
    data: T[];
    current_page: number;
    last_page: number;
    total: number;
    prev_page_url: string | null;
    next_page_url: string | null;
};
