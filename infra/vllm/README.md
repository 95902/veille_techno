# vLLM

Service `vllm` de `docker-compose.yml` : API compatible OpenAI sur le GPU local (RTX 5070, 12 Go).

## Image

- `vllm/vllm-openai@sha256:61fc8a896b0a4fbbbdc063bc4b0dbc25ce98e02b5050c24aeb7830ac02039b14`
- vLLM v0.28.0, CUDA 13.0.2, validée sur la RTX 5070 (Blackwell, sm_120).
- Figée par digest : ne jamais passer à `:latest` sans revalider la carte.

## Modèle

- Visé à l'origine : `Qwen/Qwen3-14B-AWQ`, pour la qualité du français. Ne tient pas sur la carte (voir « Historique ») ; le contrat amendé retient le 8B.
- **Servi : `Qwen/Qwen3-8B-AWQ`** (`VLLM_MODEL` dans `.env.example`), AWQ 4 bits officiel de Qwen, noyaux Marlin.
- Repli : `Qwen/Qwen3-4B` (bf16), français nettement plus faible.

## Paramètres (`.env`)

| Variable | Défaut | Rôle |
| -------- | ------ | ---- |
| `VLLM_MODEL` | `Qwen/Qwen3-8B-AWQ` | modèle servi |
| `VLLM_MAX_MODEL_LEN` | `8192` | contexte maximal ; à réduire si le KV cache ne tient pas (min. 4096) |
| `VLLM_GPU_MEMORY_UTILIZATION` | `0.80` | part de VRAM réservée |
| `VLLM_HF_HUB_OFFLINE` | `0` | `1` interdit tout accès à Hugging Face (modèle déjà en cache) |

Autres options fixes : `--reasoning-parser qwen3`, `ipc: host`, port `127.0.0.1:8000` uniquement (l'API n'a pas d'authentification).

Mesures sur la RTX 5070 (12 Go, ~1,1 Gio pris par l'affichage) :

| Modèle | `GPU_MEMORY_UTILIZATION` | Poids chargés | KV cache (8192 tokens max) |
| ------ | ------------------------ | ------------- | -------------------------- |
| `Qwen/Qwen3-8B-AWQ` | 0.80 | 5,71 Gio | 3,01 Gio, 21 936 tokens (mesure du 2026-10-19, cache de compilation chaud) |
| `Qwen/Qwen3-8B-AWQ` | 0.85 | 5,71 Gio | ❌ OOM au warm-up du sampler une fois le cache de compilation chaud (redémarrages en boucle) |
| `Qwen/Qwen3-4B` | 0.80 | 7,56 Gio | 1,18 Gio, 8 624 tokens (1,05 requête de 8192) |

Pour le 8B, 0.85 ne laisse plus de marge hors budget vLLM (warm-up du sampler) : rester à 0.80.
Si l'affichage prend plus de VRAM, descendre à 0.78 ou réduire `VLLM_MAX_MODEL_LEN` à 4096.

## Cache Hugging Face (volume `hf_cache`)

Les poids sont stockés dans le volume nommé du projet `hf_cache`
(`veille_techno_hf_cache` côté Docker), monté en lecture-écriture sur `/root/.cache/huggingface`.
Le projet ne dépend d'aucun volume d'un autre projet.

Premier démarrage (ou changement de modèle) :

1. Dans `.env`, `VLLM_HF_HUB_OFFLINE=0`.
2. `docker compose up -d vllm` : vLLM télécharge le modèle dans `hf_cache`
   (~6 Go pour `Qwen3-8B-AWQ`, ~8 Go pour `Qwen3-4B`), puis le charge.
   Suivre avec `docker compose logs -f vllm`, attendre `healthy` (`start_period` de 10 min).
3. Le premier démarrage d'un modèle peut échouer une fois sur « No available memory for the cache
   blocks » pendant la compilation torch.compile ; le service redémarre seul et passe `healthy`
   (le résultat est gardé dans le volume `vllm_compile_cache`).

Une fois le modèle en cache, repasser `VLLM_HF_HUB_OFFLINE=1` puis `docker compose up -d vllm` :
vLLM ne contacte plus Hugging Face. Les modèles présents dans le cache restent utilisables hors ligne.

Pour basculer sur le repli : `VLLM_MODEL=Qwen/Qwen3-4B`, `VLLM_GPU_MEMORY_UTILIZATION=0.80`
(et `VLLM_HF_HUB_OFFLINE=0` s'il n'est pas encore en cache), `docker compose up -d vllm`,
puis `curl -s 127.0.0.1:8000/v1/models` doit lister `Qwen/Qwen3-4B`.

## Comparaison 8B / 4B (2026-10-19)

Mêmes 3 dépêches IA en anglais (~300 mots), prompt système du worker, `temperature=0.3`, thinking désactivé.

| Modèle | Phrases (3 demandées) | Latence / résumé | `reasoning_content` |
| ------ | --------------------- | ---------------- | ------------------- |
| `Qwen/Qwen3-8B-AWQ` | 7, 9, 8 | 3,4 s, 2,8 s, 3,8 s | null |
| `Qwen/Qwen3-4B` | 8, 7, 8 | 5,3 s, 4,7 s, 4,2 s | null |

Les deux modèles rendent 3 paragraphes au lieu de 3 phrases. Le 8B fait moins d'anglicismes et
de contresens (4B : « réinforcement learning », « trader la qualité », « a entré un nouveau stade »,
« L'Accord » pour l'AI Act, « son partage » pour « sa part ») ; il garde quelques fautes
(« un fenêtre de contexte », « d'Nvidia », « huit points percent »).

## Historique : échec de Qwen3-14B-AWQ

Constat du 2026-10-19 : `Qwen/Qwen3-14B-AWQ` échoue au chargement (`torch.OutOfMemoryError`
dans `auto_awq.py::_convert_awq_to_standard_format`, ~10,1 Gio déjà alloués sur 11,49 Gio,
l'affichage en occupant ~1,1 Gio). L'échec survient avant le dimensionnement du KV cache :
réduire `VLLM_MAX_MODEL_LEN` (4096) ou `VLLM_GPU_MEMORY_UTILIZATION` (0,80) ne change rien.

## Thinking désactivé par requête

Qwen3 raisonne par défaut. Un résumé n'en a pas besoin : chaque requête envoie

```python
extra_body={"chat_template_kwargs": {"enable_thinking": False}}
```

Le serveur tourne avec `--reasoning-parser qwen3`, sans lequel le flag peut être ignoré.

## Vérifier

```sh
docker compose ps vllm                     # healthy
curl -s 127.0.0.1:8000/v1/models           # liste le modèle de .env
ss -ltn | grep 8000                        # écoute sur 127.0.0.1 seulement
```
