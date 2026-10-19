<?php

namespace Database\Seeders;

use App\Models\Category;
use Illuminate\Database\Seeder;

class CategorySeeder extends Seeder
{
    /**
     * Starting categories. The description is sent to the LLM to guide its choice;
     * "autre" is the last-resort slug. updateOrCreate: re-seeding rewrites the descriptions.
     */
    public const CATEGORIES = [
        'modeles' => [
            'name' => 'Modèles',
            'description' => 'Sortie ou nouvelle version d\'un modèle d\'IA précis (LLM, vision, audio, vidéo), poids ouverts, capacités, architecture, taille ou prix d\'un modèle. Ex. : lancement de GPT, Gemini, Claude, Llama, Qwen ou Mistral, nouveau modèle open source, comparatif de modèles.',
        ],
        'outils-dev' => [
            'name' => 'Outils dev',
            'description' => 'Ce qu\'un développeur installe ou utilise : bibliothèques, CLI, SDK, API, frameworks d\'agents, assistants de code (Copilot, Cursor, Claude Code), serveurs d\'inférence, déploiement, MLOps, nouvelle version d\'un outil dev, d\'un langage ou d\'une base de données (même sans lien direct avec l\'IA), tutoriel ou retour d\'expérience technique.',
        ],
        'recherche' => [
            'name' => 'Recherche',
            'description' => 'Travaux scientifiques : articles de recherche (arXiv), benchmarks et jeux de données, nouvelles méthodes d\'entraînement ou d\'évaluation, résultats expérimentaux, études académiques.',
        ],
        'reglementation' => [
            'name' => 'Réglementation',
            'description' => 'Actions des pouvoirs publics et du droit : lois, AI Act, RGPD, droit d\'auteur, procès et décisions de justice, politique et décisions gouvernementales, conformité, gouvernance, éthique.',
        ],
        'securite' => [
            'name' => 'Sécurité',
            'description' => 'Risques et incidents : vulnérabilités, injection de prompt, cyberattaques, fuites de données, cybersécurité, incidents de sûreté de l\'IA, alignement, deepfakes, désinformation, usages malveillants.',
        ],
        'business' => [
            'name' => 'Business',
            'description' => 'Argent et marché : levées de fonds, valorisations, rachats, résultats financiers, financement de data centers et de puces, partenariats, stratégie et produits grand public des entreprises, adoption en entreprise, marché, emploi.',
        ],
        'autre' => [
            'name' => 'Autre',
            'description' => 'Dernier recours : seulement si aucune autre catégorie ne convient, même partiellement.',
        ],
    ];

    public function run(): void
    {
        foreach (self::CATEGORIES as $slug => $attributes) {
            Category::updateOrCreate(['slug' => $slug], $attributes);
        }
    }
}
