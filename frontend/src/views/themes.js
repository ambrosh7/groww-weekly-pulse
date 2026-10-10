import { badge, escapeHtml, ratingTone } from "../utils.js";

export function renderThemes({ themes, pulse }) {
  const cards = themes
    .map((t, index) => {
      const tone = ratingTone(t.avg_rating);
      const lowShare =
        t.avg_rating < 2.5
          ? badge("Low-star share elevated", "warning")
          : badge("Watch", "neutral");
      return `
        <article class="group relative overflow-hidden panel p-space-lg pl-space-xl">
          <div class="absolute left-0 top-0 bottom-0 w-1.5 ${tone === "danger" ? "bg-error" : tone === "warning" ? "bg-tertiary-container" : "bg-primary"}"></div>
          <div class="flex flex-wrap items-start justify-between gap-space-sm mb-space-md">
            <div class="flex items-center gap-space-sm">
              <span class="w-8 h-8 rounded-full bg-surface-container flex items-center justify-center font-headline-sm text-primary">#${index + 1}</span>
              <div>
                <h2 class="font-headline-md text-headline-md text-on-surface group-hover:text-primary transition-colors">${escapeHtml(t.label)}</h2>
                <p class="font-label-sm text-label-sm text-on-surface-variant font-code-tabular">${escapeHtml(t.theme_id)} · rank ${t.rank_score.toFixed(3)}</p>
              </div>
            </div>
            <div class="flex flex-wrap items-center gap-space-xs">
              ${badge(`${t.count} reviews`, "primary")}
              ${badge(`${t.avg_rating.toFixed(2)}★ avg`, tone === "danger" ? "danger" : tone === "warning" ? "warning" : "neutral")}
              ${lowShare}
            </div>
          </div>
          <p class="font-body-md text-body-md text-on-surface">${escapeHtml(t.insight || "No insight available.")}</p>
        </article>`;
    })
    .join("");

  return `
    <section class="flex flex-col gap-space-xl">
      <header class="flex flex-col gap-space-xs">
        <div class="flex flex-wrap items-center gap-space-sm">
          ${badge("Theme engine", "primary")}
          <span class="font-code-tabular text-code-tabular text-on-surface-variant">${themes.length} clusters · ${pulse.review_count} reviews</span>
        </div>
        <h1 class="font-display-lg text-display-lg text-on-surface tracking-tight">Themes</h1>
        <p class="font-body-md text-body-md text-on-surface-variant max-w-3xl">
          Ranked friction themes from Play Store verbatims. Use this board to prioritize product and support focus for the week.
        </p>
      </header>
      <div class="flex flex-col gap-space-md stagger">${cards}</div>
    </section>`;
}
