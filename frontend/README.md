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

After `python -m src run --local-only` (or `--deliver`):

```bash
cp ../data/output/pulse.json public/data/pulse.json
```

Rebuild the reviews fixture if the sample CSV changed (from repo root):

```bash
# optional: regenerate reviews.json from the sample CSV using the same helper used at scaffold time
```

## Build

```bash
npm run build
npm run preview
```
