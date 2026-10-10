import { badge, escapeHtml, formatDate, stars } from "../utils.js";

export function renderReviews({ reviews, themes }) {
  const themeOptions = [
    `<option value="all">All themes</option>`,
    ...themes.map(
      (t) => `<option value="${escapeHtml(t.theme_id)}">${escapeHtml(t.label)}</option>`,
    ),
    `<option value="other">Other</option>`,
  ].join("");

  const rows = reviews
    .map(
      (r) => `
      <tr class="review-row border-b border-outline-variant/40 hover:bg-surface-container transition-colors" data-theme="${escapeHtml(r.theme_id)}" data-rating="${r.rating}" data-text="${escapeHtml(r.text.toLowerCase())}">
        <td class="px-space-md py-3 font-code-tabular text-code-tabular text-on-surface-variant whitespace-nowrap">${escapeHtml(formatDate(r.date))}</td>
        <td class="px-space-md py-3 text-tertiary whitespace-nowrap">${stars(r.rating)} <span class="text-on-surface-variant">(${r.rating})</span></td>
        <td class="px-space-md py-3">${badge(r.theme_label, "neutral")}</td>
        <td class="px-space-md py-3 font-body-sm text-body-sm text-on-surface max-w-xl">${escapeHtml(r.text)}</td>
      </tr>`,
    )
    .join("");

  return `
    <section class="flex flex-col gap-space-xl">
      <header class="flex flex-col gap-space-xs">
        <div class="flex flex-wrap items-center gap-space-sm">
          ${badge("Explorer", "primary")}
          <span class="font-code-tabular text-code-tabular text-on-surface-variant" id="review-count">${reviews.length} reviews</span>
        </div>
        <h1 class="font-display-lg text-display-lg text-on-surface tracking-tight">Reviews</h1>
        <p class="font-body-md text-body-md text-on-surface-variant max-w-3xl">
          Filterable Play Store corpus used for theming. Anonymous — no reviewer names.
        </p>
      </header>

      <div class="panel panel-static overflow-hidden">
        <div class="sticky top-16 z-10 flex flex-wrap items-center gap-space-sm p-space-md shell-header backdrop-blur-xl border-b border-outline-variant/40">
          <label class="flex items-center gap-space-xs px-space-md py-2 rounded-lg bg-surface-container">
            <span class="material-symbols-outlined text-[16px] text-on-surface-variant">search</span>
            <input id="review-search" type="search" placeholder="Search review text…" class="bg-transparent outline-none font-body-sm text-body-sm text-on-surface min-w-[180px]" />
          </label>
          <select id="review-theme" class="px-space-md py-2 rounded-lg bg-surface-container text-on-surface font-label-md text-label-md outline-none">
            ${themeOptions}
          </select>
          <select id="review-rating" class="px-space-md py-2 rounded-lg bg-surface-container text-on-surface font-label-md text-label-md outline-none">
            <option value="all">All ratings</option>
            <option value="1">1★</option>
            <option value="2">≤2★</option>
            <option value="3">≤3★</option>
            <option value="4">≤4★</option>
            <option value="5">5★ only</option>
          </select>
        </div>

        <div class="overflow-x-auto">
          <table class="w-full text-left">
            <thead class="sticky top-0 bg-surface-container">
              <tr class="border-b border-outline-variant/60">
                <th class="px-space-md py-3 font-label-sm text-label-sm uppercase text-on-surface-variant">Date</th>
                <th class="px-space-md py-3 font-label-sm text-label-sm uppercase text-on-surface-variant">Rating</th>
                <th class="px-space-md py-3 font-label-sm text-label-sm uppercase text-on-surface-variant">Theme</th>
                <th class="px-space-md py-3 font-label-sm text-label-sm uppercase text-on-surface-variant">Review</th>
              </tr>
            </thead>
            <tbody id="review-tbody">${rows}</tbody>
          </table>
        </div>
        <div id="review-empty" class="hidden p-space-xl text-center font-body-md text-body-md text-on-surface-variant">
          No reviews match these filters.
        </div>
      </div>
    </section>`;
}

export function bindReviewsFilters(root = document) {
  const search = root.querySelector("#review-search");
  const theme = root.querySelector("#review-theme");
  const rating = root.querySelector("#review-rating");
  const rows = [...root.querySelectorAll(".review-row")];
  const countEl = root.querySelector("#review-count");
  const empty = root.querySelector("#review-empty");
  const tbody = root.querySelector("#review-tbody");
  if (!search || !theme || !rating) return;

  const apply = () => {
    const q = search.value.trim().toLowerCase();
    const themeVal = theme.value;
    const ratingVal = rating.value;
    let visible = 0;

    rows.forEach((row) => {
      const rowTheme = row.dataset.theme;
      const rowRating = Number(row.dataset.rating);
      const text = row.dataset.text || "";
      let ok = true;
      if (themeVal !== "all" && rowTheme !== themeVal) ok = false;
      if (ratingVal === "5" && rowRating !== 5) ok = false;
      if (["1", "2", "3", "4"].includes(ratingVal) && rowRating > Number(ratingVal)) ok = false;
      if (q && !text.includes(q)) ok = false;
      row.classList.toggle("hidden", !ok);
      if (ok) visible += 1;
    });

    if (countEl) countEl.textContent = `${visible} reviews`;
    if (empty && tbody) {
      empty.classList.toggle("hidden", visible !== 0);
      tbody.classList.toggle("hidden", visible === 0);
    }
  };

  search.addEventListener("input", apply);
  theme.addEventListener("change", apply);
  rating.addEventListener("change", apply);
}
