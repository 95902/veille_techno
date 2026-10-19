#!/bin/bash
# Crée les rôles applicatifs, l'extension unaccent dans la base $POSTGRES_DB et la base de test veille_test.
# Exécuté une seule fois par l'image postgres, au premier démarrage (volume vide).
set -euo pipefail

: "${APP_DB_PASSWORD:?APP_DB_PASSWORD manquant}"
: "${WORKER_DB_PASSWORD:?WORKER_DB_PASSWORD manquant}"

psql -v ON_ERROR_STOP=1 \
  --username "$POSTGRES_USER" \
  --dbname "$POSTGRES_DB" \
  -v db="$POSTGRES_DB" \
  -v app_pw="$APP_DB_PASSWORD" \
  -v worker_pw="$WORKER_DB_PASSWORD" <<'SQL'
CREATE ROLE veille_app LOGIN PASSWORD :'app_pw';
CREATE ROLE veille_worker LOGIN PASSWORD :'worker_pw';

-- veille_app possède la base et le schéma public : seul propriétaire du schéma (migrations Laravel).
ALTER DATABASE :"db" OWNER TO veille_app;
ALTER SCHEMA public OWNER TO veille_app;
REVOKE ALL ON SCHEMA public FROM PUBLIC;
REVOKE CREATE ON DATABASE :"db" FROM PUBLIC;
-- Pas de tables temporaires pour PUBLIC (donc veille_worker). veille_app, propriétaire de la base,
-- garde TEMPORARY par ses droits de propriétaire ; Laravel n'en a de toute façon pas besoin.
REVOKE TEMPORARY ON DATABASE :"db" FROM PUBLIC;

-- veille_worker : connexion et accès au schéma seulement, aucun DDL. Aucun privilège par
-- défaut sur les tables : les droits table par table (SELECT sources/categories,
-- SELECT/INSERT/UPDATE articles) viennent d'une migration Laravel, exécutée par veille_app.
GRANT CONNECT ON DATABASE :"db" TO veille_worker;
GRANT USAGE ON SCHEMA public TO veille_worker;

-- Recherche plein texte sans accents.
CREATE EXTENSION IF NOT EXISTS unaccent;

-- Base des tests Pest du groupe pgsql (RefreshDatabase la vide) : jamais la base de l'app.CREATE DATABASE veille_test OWNER veille_app;
SQL
