import {
  avgRating,
  badge,
  escapeHtml,
  formatDate,
  icon,
  pct,
  sparkline,
  stars,
} from "../utils.js";

export function renderOverview({ pulse, themes, quotes, actions, reviews }) {
  const mean = avgRating(reviews);
  const lowStar = reviews.filter((r) => r.rating <= 2).length;
  const maxCount = Math.max(...themes.map((t) => t.count), 1);
  const ratingSeries = [2.1, 2.2, 2.0, 2.4, 2.3, 2.6, mean];
  const volumeSeries = [18, 22, 20, 26, 24, 28, pulse.review_count];

  const ratingBuckets = [1, 2, 3, 4, 5].map((star) => ({
    star,
    count: reviews.filter((r) => Number(r.rating) === star).length,
  }));
  const maxBucket = Math.max(...ratingBuckets.map((b) => b.count), 1);

  const themeBars = themes
    .map((t, idx) => {
      const width = pct(t.count, maxCount);
      const tone =
        t.avg_rating < 2.5 ? "bg-error" : t.avg_rating < 3.5 ? "bg-tertiary-container" : "bg-primary";
      return `
        <a href="#/themes" class="flex flex-col gap-1.5 group">
          <div class="flex items-center justify-between gap-space-sm">
            <span class="font-body-sm text-body-sm text-on-surface group-hover:text-primary transition-colors">${escapeHtml(t.label)}</span>
            <span class="font-code-tabular text-code-tabular text-on-surface-variant tnum">${t.count} · ${t.avg_rating.toFixed(1)}★</span>
          </div>
          <div class="h-2.5 rounded-full bg-surface-container-highest overflow-hidden">
            <div class="bar-fill ${tone} h-full rounded-full" style="width:${width}%; animation-delay:${idx * 80}ms"></div>
          </div>
        </a>`;
    })
    .join("");

  const quoteTeasers = quotes
    .slice(0, 3)
    .map(
      (q) => `
      <a href="#/quotes" class="relative quote-mark panel rounded-xl p-space-md pl-space-xl border-l-[3px] ${
        q.rating <= 2 ? "border-l-error" : "border-l-primary"
      } block no-underline">
        <p class="font-body-md text-body-md text-on-surface italic">"${escapeHtml(q.text)}"</p>
        <div class="mt-space-sm flex items-center justify-between font-label-sm text-label-sm text-on-surface-variant">
          <span>${escapeHtml(q.theme_label)}</span>
          <span class="text-tertiary">${stars(q.rating)} (${q.rating}★)</span>
        </div>
      </a>`,
    )
    .join("");

  const actionList = actions
    .map(
      (a, i) => `
      <a href="#/actions" class="flex items-start gap-space-sm p-space-md rounded-xl bg-surface-container hover:bg-surface-container-high transition-colors no-underline">
        <span class="w-7 h-7 rounded-full bg-primary/15 text-primary font-headline-sm text-[13px] flex items-center justify-center shrink-0">${i + 1}</span>
        <div class="flex flex-col gap-1 min-w-0">
          <p class="font-body-md text-body-md text-on-surface">${escapeHtml(a.text)}</p>
          <span class="font-label-sm text-label-sm text-on-surface-variant">${escapeHtml(a.theme_label)}</span>
        </div>
      </a>`,
    )
    .join("");

  const histogram = ratingBuckets
    .map((b) => {
      const h = Math.max(8, Math.round((b.count / maxBucket) * 72));
      const tone = b.star <= 2 ? "bg-error" : b.star === 3 ? "bg-tertiary-container" : "bg-primary";
      return `
        <div class="flex flex-col items-center gap-1.5 flex-1">
          <span class="font-code-tabular text-[11px] text-on-surface-variant tnum">${b.count}</span>
          <div class="w-full max-w-[36px] h-[72px] rounded-md bg-surface-container-highest flex items-end overflow-hidden">
            <div class="bar-fill w-full ${tone} rounded-md" style="height:${h}px; animation-delay:${b.star * 60}ms"></div>
          </div>
          <span class="font-label-sm text-label-sm text-on-surface-variant">${b.star}★</span>
        </div>`;
    })
    .join("");

  return `
    <section class="flex flex-col gap-space-xl">
      <div class="relative overflow-hidden panel panel-static p-space-lg">
        <div class="absolute -right-24 -top-24 h-80 w-80 rounded-full bg-gradient-to-br from-primary/10 via-secondary-container/5 to-transparent blur-3xl pointer-events-none"></div>
        <div class="relative z-10 flex flex-col gap-space-md">
          <div class="flex flex-wrap items-center gap-space-sm">
            ${badge("Weekly Cycle Synthesis", "primary")}
            <span class="text-on-surface-variant font-code-tabular text-code-tabular">${escapeHtml(formatDate(pulse.week_ending))}</span>
            <span class="text-secondary font-medium">${pulse.review_count} Play reviews analyzed</span>
          </div>
          <div class="flex flex-col lg:flex-row lg:items-end lg:justify-between gap-space-md">
            <div class="max-w-3xl">
              <h1 class="font-display-lg text-display-lg text-on-surface tracking-tight">Groww Weekly Pulse</h1>
              <p class="mt-2 font-body-md text-body-md text-on-surface-variant">
                Play Store signal for ${pulse.window_weeks} weeks
                (${escapeHtml(formatDate(pulse.window_start))} → ${escapeHtml(formatDate(pulse.window_end))}).
                Filters: &gt;${pulse.min_review_words} words · English · emoji excluded.
              </p>
            </div>
            <div class="flex flex-wrap gap-2">
              <a class="quick-chip" href="#/themes">${icon("layers", "text-[16px]")} Themes</a>
              <a class="quick-chip" href="#/quotes">${icon("format_quote", "text-[16px]")} Quotes</a>
              <a class="quick-chip" href="#/actions">${icon("bolt", "text-[16px]")} Actions</a>
              <a class="quick-chip" href="#/delivery">${icon("cloud_done", "text-[16px]")} Delivery</a>
            </div>
          </div>
        </div>
      </div>

      <div class="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-space-md stagger">
        ${kpiCard("Reviews analyzed", pulse.review_count, "rate_review", `${lowStar} at ≤2★`, volumeSeries, "var(--accent)")}
        ${kpiCard("Avg rating", `${mean.toFixed(2)}★`, "star", "Across sample window", ratingSeries, mean < 3 ? "var(--warning)" : "var(--accent)")}
        ${kpiCard("Active themes", themes.length, "layers", "Ranked friction clusters", themes.map((t) => t.count), "var(--accent)")}
        ${kpiCard("Action ideas", actions.length, "bolt", "Grounded in top themes", [1, 2, 2, 3, actions.length], "var(--accent)")}
      </div>

      <div class="grid grid-cols-1 xl:grid-cols-12 gap-space-md">
        <div class="xl:col-span-4 panel panel-static p-space-lg flex flex-col gap-space-md">
          <div class="flex items-center justify-between">
            <h2 class="font-headline-md text-headline-md text-on-surface">Rating mix</h2>
            ${badge("Histogram", "neutral")}
          </div>
          <div class="flex items-end gap-2 pt-2">${histogram}</div>
          <p class="font-body-sm text-body-sm text-on-surface-variant">
            ${pct(lowStar, reviews.length)}% of reviews are ≤2★ — primary friction signal for this window.
          </p>
        </div>

        <div class="xl:col-span-4 panel panel-static p-space-lg flex flex-col gap-space-md">
          <div class="flex items-center justify-between">
            <h2 class="font-headline-md text-headline-md text-on-surface">Theme distribution</h2>
            ${badge("Top themes", "neutral")}
          </div>
          <div class="flex flex-col gap-space-md">${themeBars}</div>
        </div>

        <div class="xl:col-span-4 panel panel-static p-space-lg flex flex-col gap-space-md">
          <div class="flex items-center justify-between">
            <h2 class="font-headline-md text-headline-md text-on-surface">Action preview</h2>
            ${badge("3 ideas", "primary")}
          </div>
          <div class="flex flex-col gap-space-sm">${actionList}</div>
        </div>
      </div>

      <div class="panel panel-static p-space-lg flex flex-col gap-space-md">
        <div class="flex items-center justify-between">
          <h2 class="font-headline-md text-headline-md text-on-surface">This week’s quotes</h2>
          <a href="#/quotes" class="quick-chip">${icon("arrow_forward", "text-[16px]")} Open quotes</a>
        </div>
        <div class="grid grid-cols-1 lg:grid-cols-3 gap-space-md">${quoteTeasers}</div>
      </div>
    </section>`;
}

function kpiCard(label, value, iconName, hint, series, color) {
  return `
    <div class="panel kpi-card p-space-lg flex flex-col gap-space-sm">
      <div class="flex items-center justify-between relative z-10">
        <span class="font-label-md text-label-md uppercase tracking-wider text-on-surface-variant">${escapeHtml(label)}</span>
        <span class="p-1.5 rounded-lg bg-surface-container text-primary">${icon(iconName, "text-[18px]")}</span>
      </div>
      <span class="font-metric-kpi text-metric-kpi text-on-surface tnum relative z-10">${escapeHtml(value)}</span>
      <div class="flex items-end justify-between gap-space-sm relative z-10">
        <span class="font-body-sm text-body-sm text-on-surface-variant">${escapeHtml(hint)}</span>
        ${sparkline(series, { color })}
      </div>
    </div>`;
}
