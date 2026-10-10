# Groww Weekly Pulse — Railway one-shot worker (pipeline CLI).
# MCP Docs/Gmail OAuth stays on the separate gmail-docs-mcp-server service.
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt pyproject.toml ./
RUN pip install --no-cache-dir -r requirements.txt

COPY src ./src
COPY scripts ./scripts
COPY config/settings.example.yaml ./config/settings.example.yaml
COPY data/raw/groww_play_reviews_sample.csv ./data/raw/groww_play_reviews_sample.csv
COPY data/raw/.gitkeep ./data/raw/.gitkeep
COPY data/processed/.gitkeep ./data/processed/.gitkeep
COPY data/output/.gitkeep ./data/output/.gitkeep

RUN chmod +x scripts/railway_run.sh \
    && mkdir -p frontend/public/data

CMD ["bash", "scripts/railway_run.sh"]
