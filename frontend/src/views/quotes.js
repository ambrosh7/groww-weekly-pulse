import { badge, escapeHtml, stars } from "../utils.js";

export function renderQuotes({ quotes, pulse }) {
  const cards = quotes
    .map(
      (q) => `
      <article class="relative quote-mark panel p-space-lg pl-space-xl border-l-[3px] ${
        q.rating <= 2 ? "border-l-error" : "border-l-primary"
      }">
        <div class="flex flex-wrap items-center justify-between gap-space-sm mb-space-sm">
          ${badge(q.theme_label, "neutral")}
          <span class="font-label-sm text-label-sm text-tertiary">${stars(q.rating)} (${q.rating}★)</span>
        </div>
        <p class="font-body-lg text-body-lg text-on-surface italic leading-relaxed">"${escapeHtml(q.text)}"</p>
        <div class="mt-space-md flex items-center justify-between font-code-tabular text-code-tabular text-on-surface-variant">
          <span>Anonymous Play Store verbatim</span>
          <span>${escapeHtml(q.review_id)}</span>
        </div>
      </article>`,
    )
    .join("");

  return `
    <section class="flex flex-col gap-space-xl">
      <header class="flex flex-col gap-space-xs">
        <div class="flex flex-wrap items-center gap-space-sm">
          ${badge("Verbatim evidence", "primary")}
          <span class="font-code-tabular text-code-tabular text-on-surface-variant">${quotes.length} quotes · week ${escapeHtml(pulse.week_ending)}</span>
        </div>
        <h1 class="font-display-lg text-display-lg text-on-surface tracking-tight">Quotes</h1>
        <p class="font-body-md text-body-md text-on-surface-variant max-w-3xl">
          Real user language only — no invented wording. Reviewer identities are never shown.
        </p>
      </header>
      <div class="grid grid-cols-1 lg:grid-cols-3 gap-space-md stagger">${cards}</div>
    </section>`;
}
