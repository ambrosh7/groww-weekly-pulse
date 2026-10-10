#!/usr/bin/env bash
# Railway one-shot entrypoint for the Groww pulse pipeline (Option B in deployment-plan).
set -euo pipefail

cd "$(dirname "$0")/.."

export DELIVER="${DELIVER:-true}"
export FETCH_REVIEWS="${FETCH_REVIEWS:-true}"
export USE_SAMPLE="${USE_SAMPLE:-false}"
export MAX_REVIEWS="${MAX_REVIEWS:-5000}"
export WINDOW_WEEKS="${WINDOW_WEEKS:-10}"
export MCP_BASE_URL="${MCP_BASE_URL:-https://gmail-docs-mcp-server-production.up.railway.app}"

echo "Railway pulse run — DELIVER=${DELIVER} FETCH_REVIEWS=${FETCH_REVIEWS} USE_SAMPLE=${USE_SAMPLE}"

python scripts/write_ci_settings.py

if [ "${USE_SAMPLE}" = "true" ]; then
  python -m src run -i data/raw/groww_play_reviews_sample.csv --local-only
elif [ "${FETCH_REVIEWS}" = "true" ]; then
  python -m src fetch-reviews --lang en --country in --max-reviews "${MAX_REVIEWS}"
  if [ "${DELIVER}" = "true" ]; then
    if [ -z "${MCP_HTTP_BEARER_TOKEN:-}" ]; then
      echo "MCP_HTTP_BEARER_TOKEN is required when DELIVER=true" >&2
      exit 1
    fi
    python -m src run --deliver
  else
    python -m src run --local-only
  fi
else
  if [ "${DELIVER}" = "true" ]; then
    if [ -z "${MCP_HTTP_BEARER_TOKEN:-}" ]; then
      echo "MCP_HTTP_BEARER_TOKEN is required when DELIVER=true" >&2
      exit 1
    fi
    python -m src run --deliver
  else
    python -m src run --local-only
  fi
fi

python scripts/sync_frontend_data.py || true
echo "Railway pulse run complete"
