---
objective: "docker compose up démarre nginx, app, postgres, vllm et worker-py, et le worker obtient de vLLM un résumé en français sur la RTX 5070."
status: implemented
---

# Plan: Socle technique

## Overview

| Field      | Value                                                        |
| ---------- | ------------------------------------------------------------ |
| **Goal**   | Infrastructure Compose et squelettes `web/` et `worker/`, sans métier |
| **Source** | `aidd_docs/tasks/2026_10/2026_10_19_socle-technique/contract.md` |

## Phases

| #   | Phase                                   | File                         |
| --- | --------------------------------------- | ---------------------------- |
| 1   | Infrastructure Compose, Postgres, vLLM  | [`phase-1.md`](./phase-1.md) |
| 2   | Worker Python et test vLLM              | [`phase-2.md`](./phase-2.md) |
| 3   | Application Laravel, Filament, nginx    | [`phase-3.md`](./phase-3.md) |

## Resources

| Source | Verified |
| ------ | -------- |
| `docker image inspect vllm/vllm-openai:latest` (local) | v0.28.0, CUDA 13.0.2, build du 2026-08-25, digest `sha256:61fc8a896b0a4fbbbdc063bc4b0dbc25ce98e02b5050c24aeb7830ac02039b14` |
| `nvidia-smi`, `docker info` (local) | RTX 5070 12 Go, pilote 580 / CUDA 13.0, runtime `nvidia` et CDI disponibles |
| volume `agent-editorial_vllm_hf_cache` (local) | contient `models--Qwen--Qwen3-14B-AWQ` et `models--Qwen--Qwen3-4B` |
| https://qwen.readthedocs.io/en/latest/deployment/vllm.html | Qwen3 raisonne par défaut ; désactivation par `chat_template_kwargs: {enable_thinking: false}` (via `extra_body`) |
| https://discuss.vllm.ai/t/deployment-example-for-a-qwen3-model-with-hybrid-thinking/1462 | le flag peut être ignoré sans le bon reasoning parser : servir avec `--reasoning-parser qwen3` |

## Decisions

| Decision | Why |
| -------- | --- |
| vLLM figé par digest, pas par tag | les images `latest` ont longtemps cassé sm_120 ; celle-ci est la version présente sur la machine |
| Cache de modèles externe (`agent-editorial_vllm_hf_cache`), monté en lecture seule, `HF_HUB_OFFLINE=1` | aucun téléchargement, aucune écriture dans le volume d'un autre projet |
| vLLM exposé sur `127.0.0.1:8000` uniquement | l'API n'a pas d'authentification |
| Thinking Qwen3 désactivé par requête | un résumé n'a pas besoin de raisonnement, et le raisonnement multiplie la latence et les tokens |
