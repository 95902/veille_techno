<script setup lang="ts">
import { Head, Link, router } from '@inertiajs/vue3';
import { ChevronLeft, ChevronRight, Search } from '@lucide/vue';
import { computed, ref } from 'vue';
import ArticleCard from '@/components/ArticleCard.vue';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { index, show } from '@/routes/articles';
import type {
    ArticleCategory,
    ArticleFilters,
    ArticleSummary,
    Paginated,
} from '@/types';

const props = defineProps<{
    articles: Paginated<ArticleSummary>;
    categories: ArticleCategory[];
    filters: ArticleFilters;
}>();

defineOptions({
    layout: {
        breadcrumbs: [{ title: 'Articles', href: index() }],
    },
});

const q = ref(props.filters.q);
const categorie = ref(props.filters.categorie);

/** Current filters, without the empty ones, for the URLs. */
function filterQuery(): Record<string, string> {
    return Object.fromEntries(
        Object.entries({
            q: q.value.trim(),
            categorie: categorie.value,
        }).filter(([, value]) => value !== ''),
    );
}

function applyFilters(): void {
    router.get(
        index.url({ query: filterQuery() }),
        {},
        { preserveState: true, preserveScroll: true },
    );
}

const listQuery = computed(() => {
    const query: Record<string, string | number> = Object.fromEntries(
        Object.entries(props.filters).filter(([, value]) => value !== ''),
    );

    if (props.articles.current_page > 1) {
        query.page = props.articles.current_page;
    }

    return query;
});
</script>

<template>
    <Head title="Articles" />

    <div class="flex flex-1 flex-col gap-4 p-4">
        <h1 class="sr-only">Articles</h1>

        <form
            role="search"
            class="flex flex-col gap-2 sm:flex-row"
            @submit.prevent="applyFilters"
        >
            <div class="relative flex-1">
                <Search
                    class="pointer-events-none absolute top-1/2 left-3 size-4 -translate-y-1/2 text-muted-foreground"
                />
                <Input
                    v-model="q"
                    type="search"
                    name="q"
                    maxlength="200"
                    placeholder="Rechercher…"
                    aria-label="Rechercher dans les articles"
                    class="pl-9"
                />
            </div>
            <select
                v-model="categorie"
                name="categorie"
                aria-label="Catégorie"
                class="h-9 rounded-md border border-input bg-transparent px-3 text-sm shadow-xs outline-none focus-visible:border-ring focus-visible:ring-[3px] focus-visible:ring-ring/50 dark:bg-input/30"
                @change="applyFilters"
            >
                <option value="">Toutes les catégories</option>
                <option
                    v-for="category in categories"
                    :key="category.slug"
                    :value="category.slug"
                >
                    {{ category.name }}
                </option>
            </select>
            <Button type="submit">Rechercher</Button>
        </form>

        <p class="text-sm text-muted-foreground">
            {{ articles.total }}
            {{ articles.total > 1 ? 'articles' : 'article' }}
        </p>

        <div v-if="articles.data.length" class="grid gap-3">
            <ArticleCard
                v-for="article in articles.data"
                :key="article.id"
                :article="article"
                :href="show.url(article.id, { query: listQuery })"
            />
        </div>
        <p
            v-else
            class="rounded-xl border border-dashed p-8 text-center text-sm text-muted-foreground"
        >
            Aucun article ne correspond à ces critères.
        </p>

        <nav
            v-if="articles.last_page > 1"
            aria-label="Pagination"
            class="flex items-center justify-between gap-2"
        >
            <Button
                v-if="articles.prev_page_url"
                variant="outline"
                size="sm"
                as-child
            >
                <Link :href="articles.prev_page_url" preserve-scroll>
                    <ChevronLeft /> Précédent
                </Link>
            </Button>
            <span v-else />
            <span class="text-sm text-muted-foreground">
                Page {{ articles.current_page }} / {{ articles.last_page }}
            </span>
            <Button
                v-if="articles.next_page_url"
                variant="outline"
                size="sm"
                as-child
            >
                <Link :href="articles.next_page_url">
                    Suivant <ChevronRight />
                </Link>
            </Button>
            <span v-else />
        </nav>
    </div>
</template>
