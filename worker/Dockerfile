FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:0.9.27 /uv /usr/local/bin/uv

# supercronic (cron pour conteneurs) du service worker-cron : binaire figé, somme SHA-256
# vérifiée au build (SHA-1 publiée par la release : e63c11a9726b775a6a11801e81af4f3fb926aa68).
ADD --chmod=0755 \
    --checksum=sha256:a53ae236602c7338aba3fbaff40bda6300eae3b9fedb8261eb06cfe3724430c1 \
    https://github.com/aptible/supercronic/releases/download/v0.2.49/supercronic-linux-amd64 \
    /usr/local/bin/supercronic

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    PATH="/opt/venv/bin:$PATH"

WORKDIR /app

COPY pyproject.toml uv.lock README.md ./
RUN uv sync --frozen --no-dev --no-install-project

COPY src ./src
RUN uv sync --frozen --no-dev

COPY crontab ./crontab

CMD ["python", "-m", "veille_worker.smoke"]
