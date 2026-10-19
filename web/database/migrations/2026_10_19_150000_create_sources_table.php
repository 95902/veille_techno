<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    /**
     * Run the migrations.
     */
    public function up(): void
    {
        Schema::create('sources', function (Blueprint $table) {
            $table->id();
            $table->string('name');
            $table->string('feed_url', 2048)->unique();
            // rss : article extrait de sa page ; arxiv : résumé du flux, sans extraction.
            $table->string('type', 16)->default('rss');
            $table->boolean('active')->default(true);
            // Plafond d'entrées lues par collecte (arXiv publie des centaines d'articles par jour).
            $table->unsignedSmallInteger('max_items_per_run')->default(20);
            $table->timestamps();
        });
    }

    /**
     * Reverse the migrations.
     */
    public function down(): void
    {
        Schema::dropIfExists('sources');
    }
};
