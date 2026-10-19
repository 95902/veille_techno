<script setup lang="ts">
import { Head, Link, usePage } from '@inertiajs/vue3';
import { ArrowLeft, ExternalLink } from '@lucide/vue';
import { computed } from 'vue';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { formatArticleDate, summaryLines } from '@/lib/articles';
import { index } from '@/routes/articles';
import type { ArticleDetail } from '@/types';

const props = defineProps<{
    article: ArticleDetail;
}>();

defineOptions({
    layout: {
        breadcrumbs: [{ title: 'Articles', href: index() }],
    },
});

const page = usePage();

/** Back to the list with the filters and page the reader came from. */
const backHref = computed(() => {
    const params = new URL(page.url, 'http://localhost').searchParams;

    return index({ query: Object.fromEntries(params) });
});

const lines = computed(() => summaryLines(props.article.summary));
</script>

<template>
    <Head :title="article.title_fr" />

    <article class="mx-auto flex w-full max-w-3xl flex-col gap-6 p-4">
        <Link
            :href="backHref"
            class="inline-flex w-fit items-center gap-1 text-sm text-muted-foreground hover:text-foreground"
        >
            <ArrowLeft class="size-4" /> Retour à la liste
        </Link>

        <header class="flex flex-col gap-2">
            <div
                class="flex flex-wrap items-center gap-2 text-sm text-muted-foreground"
            >
                <Badge v-if="article.category" variant="secondary">
                    {{ article.category.name }}
                </Badge>
                <span>{{ article.source }}</span>
                <span aria-hidden="true">·</span>
                <time :datetime="article.published_at ?? undefined">
                    {{ formatArticleDate(article.published_at) }}
                </time>
            </div>
            <h1 class="text-2xl font-semibold tracking-tight">
                {{ article.title_fr }}
            </h1>
            <p class="text-sm text-muted-foreground">
                Titre d'origine :
                <span class="italic">{{ article.title }}</span>
            </p>
        </header>

        <section
            aria-label="Résumé"
            class="flex flex-col gap-2 leading-relaxed"
        >
            <p v-for="(line, i) in lines" :key="i">{{ line }}</p>
        </section>

        <Button as-child class="w-fit">
            <a :href="article.url" target="_blank" rel="noopener noreferrer">
                Lire l'article d'origine <ExternalLink />
            </a>
        </Button>
    </article>
</template>
