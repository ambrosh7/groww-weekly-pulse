# Groww Weekly Pulse — Frontend

Executive dashboard UI generated from the Stitch design system in `stitch_groww_weekly_review_pulse/`.

## Features

- Light / dark theme toggle (persisted in `localStorage`)
- Dashboards: Overview · Themes · Quotes · Actions · Reviews · Delivery
- Data from `public/data/pulse.json` and `public/data/reviews.json`

## Run

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173

## Refresh data from the pipeline

From repo root after `python -m src run --local-only` (or `--deliver`):

```bash
python scripts/sync_frontend_data.py
```

This updates `public/data/pulse.json` and `public/data/reviews.json` (theme labels from `themes.json`). Monthly GitHub Actions commits the same files so Vercel redeploys automatically.

Optional build-time env: `VITE_DATA_BASE` — absolute origin prefix for `/data/*.json`.

## Build

```bash
npm run build
npm run preview
```
