<script setup lang="ts">
import { Link } from '@inertiajs/vue3';
import type { InertiaLinkProps } from '@inertiajs/vue3';
import { computed } from 'vue';
import { Badge } from '@/components/ui/badge';
import {
    Card,
    CardContent,
    CardDescription,
    CardHeader,
    CardTitle,
} from '@/components/ui/card';
import { formatArticleDate, summaryLines } from '@/lib/articles';
import type { ArticleSummary } from '@/types';

const props = defineProps<{
    article: ArticleSummary;
    href: NonNullable<InertiaLinkProps['href']>;
}>();

const lines = computed(() => summaryLines(props.article.summary));
</script>

<template>
    <Link
        :href="href"
        class="block rounded-xl focus-visible:ring-[3px] focus-visible:ring-ring/50 focus-visible:outline-none"
    >
        <Card class="gap-3 py-4 transition-colors hover:bg-accent/40">
            <CardHeader class="gap-2 px-4">
                <CardDescription class="flex flex-wrap items-center gap-2">
                    <Badge v-if="article.category" variant="secondary">
                        {{ article.category.name }}
                    </Badge>
                    <span>{{ article.source }}</span>
                    <span aria-hidden="true">·</span>
                    <time :datetime="article.published_at ?? undefined">
                        {{ formatArticleDate(article.published_at) }}
                    </time>
                </CardDescription>
                <CardTitle class="text-base leading-snug">
                    {{ article.title_fr }}
                </CardTitle>
            </CardHeader>
            <CardContent class="px-4">
                <ul class="space-y-1 text-sm text-muted-foreground">
                    <li v-for="(line, index) in lines" :key="index">
                        {{ line }}
                    </li>
                </ul>
            </CardContent>
        </Card>
    </Link>
</template>
