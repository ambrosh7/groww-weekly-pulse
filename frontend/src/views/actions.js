import { badge, escapeHtml, icon } from "../utils.js";

const STATUS_META = {
  in_review: {
    label: "In Review",
    chip: "bg-tertiary/10 text-tertiary",
    edge: "from-error via-tertiary-container to-error",
    priorityLabel: "P0 · Immediate",
    priorityChip: "bg-error-container/40 text-error",
  },
  suggested: {
    label: "Suggested (New)",
    chip: "bg-secondary/15 text-secondary",
    edge: "from-secondary to-primary-container",
    priorityLabel: "P1 · High Priority",
    priorityChip: "bg-secondary/15 text-secondary",
  },
  done: {
    label: "Done / Shipped",
    chip: "bg-primary-container/20 text-primary",
    edge: "from-primary to-primary",
    priorityLabel: "P1 · High Priority",
    priorityChip: "bg-primary/10 text-primary",
  },
};

export function renderActions({ actions, pulse, quotes }) {
  const cards = actions
    .map((action) => {
      const meta = STATUS_META[action.status] || STATUS_META.suggested;
      const relatedQuotes = quotes.filter((q) => q.theme_id === action.theme_id);
      const problem =
        action.insight ||
        relatedQuotes[0]?.text ||
        "Friction observed in Play Store reviews for this theme.";
      return `
        <article class="group relative overflow-hidden panel transition-all duration-300">
          <div class="absolute left-0 top-0 bottom-0 w-1.5 bg-gradient-to-b ${meta.edge}"></div>
          <div class="p-space-lg flex flex-col gap-space-md pl-space-xl">
            <div class="flex flex-wrap items-center justify-between gap-space-sm">
              <div class="flex flex-wrap items-center gap-space-sm">
                <span class="inline-flex items-center gap-1.5 px-3 py-1 rounded-full ${meta.priorityChip} font-headline-sm text-[13px] font-bold tracking-wide uppercase">
                  ${icon(action.status === "done" ? "verified" : action.status === "in_review" ? "crisis_alert" : "flag", "text-[15px]")}
                  ${meta.priorityLabel}
                </span>
                <span class="inline-flex items-center gap-1.5 px-3 py-1 rounded-full ${meta.chip} font-label-md text-label-md">
                  <span class="w-2 h-2 rounded-full bg-current"></span>
                  ${meta.label}
                </span>
                <span class="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg bg-surface-container-highest text-on-surface-variant font-label-sm text-label-sm">
                  Theme: ${escapeHtml(action.theme_label)}
                </span>
              </div>
              <span class="font-label-sm text-label-sm text-on-surface-variant">${action.count} reviews · ${Number(action.avg_rating).toFixed(2)}★</span>
            </div>

            <h2 class="font-headline-lg text-headline-lg text-on-surface group-hover:text-primary transition-colors">
              ${escapeHtml(action.text)}
            </h2>

            <div class="grid grid-cols-1 lg:grid-cols-2 gap-space-md">
              <div class="rounded-lg bg-surface-container p-space-md flex flex-col gap-space-xs">
                <div class="flex items-center gap-space-xs text-error font-label-md text-label-md uppercase tracking-wide">
                  ${icon("error_outline", "text-[18px]")}
                  <span>Observed Friction</span>
                </div>
                <p class="font-body-md text-body-md text-on-surface">${escapeHtml(problem)}</p>
              </div>
              <div class="rounded-lg bg-surface-container p-space-md flex flex-col gap-space-xs">
                <div class="flex items-center gap-space-xs text-primary font-label-md text-label-md uppercase tracking-wide">
                  ${icon("task_alt", "text-[18px]")}
                  <span>Recommended Action</span>
                </div>
                <p class="font-body-md text-body-md text-on-surface">${escapeHtml(action.text)}</p>
              </div>
            </div>

            ${
              relatedQuotes.length
                ? `<div class="rounded-lg bg-surface-container-high/60 p-space-sm">
                    <p class="font-label-sm text-label-sm text-on-surface-variant mb-1">Evidence quote</p>
                    <p class="font-body-sm text-body-sm text-on-surface italic">"${escapeHtml(relatedQuotes[0].text)}"</p>
                  </div>`
                : ""
            }
          </div>
        </article>`;
    })
    .join("");

  return `
    <section class="flex flex-col gap-space-xl">
      <div class="relative overflow-hidden panel panel-static p-space-lg">
        <div class="absolute -right-24 -top-24 h-80 w-80 rounded-full bg-gradient-to-br from-primary/10 via-secondary-container/5 to-transparent blur-3xl pointer-events-none"></div>
        <div class="relative z-10 flex flex-col lg:flex-row lg:items-center justify-between gap-space-lg">
          <div class="flex flex-col gap-space-xs max-w-3xl">
            <div class="flex flex-wrap items-center gap-space-sm">
              ${badge("Weekly Cycle Synthesis", "primary")}
              <span class="font-code-tabular text-code-tabular text-on-surface-variant">Week Ending ${escapeHtml(pulse.week_ending)}</span>
              <span class="text-secondary font-medium">${pulse.review_count} Store Verbatims Evaluated</span>
            </div>
            <h1 class="font-display-lg text-display-lg text-on-surface tracking-tight">Prioritized Action Matrix</h1>
            <p class="font-body-md text-body-md text-on-surface-variant">
              ${actions.length} high-leverage product initiatives synthesized from ${pulse.review_count} Play Store reviews across ${pulse.themes?.length || 0} key friction themes.
            </p>
          </div>
        </div>
      </div>

      <div class="grid grid-cols-1 md:grid-cols-3 gap-space-md">
        ${stat("Total pipeline", String(actions.length), "Active matrix tasks")}
        ${stat("In review", String(actions.filter((a) => a.status === "in_review").length), "Needs owner decision")}
        ${stat("Suggested", String(actions.filter((a) => a.status === "suggested").length), "Ready for sprint intake")}
      </div>

      <div class="flex flex-col gap-space-lg">
        <div class="flex items-center gap-space-sm">
          <h2 class="font-headline-lg text-headline-lg text-on-surface">Execution Plan</h2>
          ${badge(`${actions.length} Initiatives`, "neutral")}
        </div>
        ${cards}
      </div>
    </section>`;
}

function stat(label, value, hint) {
  return `
    <div class="panel kpi-card p-space-lg">
      <span class="font-label-md text-label-md uppercase tracking-wider text-on-surface-variant">${escapeHtml(label)}</span>
      <div class="mt-space-sm font-metric-kpi text-metric-kpi text-on-surface tnum">${escapeHtml(value)}</div>
      <p class="mt-space-xs font-body-sm text-body-sm text-on-surface-variant">${escapeHtml(hint)}</p>
    </div>`;
}
