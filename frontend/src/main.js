import { loadDashboardData } from "./data.js";
import { bindShellEvents, renderShell } from "./shell.js";
import { initTheme, syncThemeControls } from "./theme.js";
import { renderOverview } from "./views/overview.js";
import { renderThemes } from "./views/themes.js";
import { renderQuotes } from "./views/quotes.js";
import { renderActions } from "./views/actions.js";
import { bindReviewsFilters, renderReviews } from "./views/reviews.js";
import { renderDelivery } from "./views/delivery.js";

const ROUTES = new Set([
  "overview",
  "themes",
  "quotes",
  "actions",
  "reviews",
  "delivery",
]);

let data = null;

function currentRoute() {
  const hash = window.location.hash.replace(/^#\/?/, "");
  const route = hash.split("?")[0] || "overview";
  return ROUTES.has(route) ? route : "overview";
}

function renderView(route, payload) {
  switch (route) {
    case "themes":
      return renderThemes(payload);
    case "quotes":
      return renderQuotes(payload);
    case "actions":
      return renderActions(payload);
    case "reviews":
      return renderReviews(payload);
    case "delivery":
      return renderDelivery(payload);
    case "overview":
    default:
      return renderOverview(payload);
  }
}

async function render() {
  const app = document.getElementById("app");
  if (!app) return;

  if (!data) {
    app.innerHTML = `
      <div class="min-h-screen flex items-center justify-center shell-main text-on-surface">
        <div class="flex items-center gap-3 font-body-md text-body-md text-on-surface-variant">
          <span class="material-symbols-outlined animate-spin text-primary">progress_activity</span>
          Loading Weekly Pulse console…
        </div>
      </div>`;
    try {
      data = await loadDashboardData();
    } catch (err) {
      app.innerHTML = `
        <div class="min-h-screen flex items-center justify-center shell-main px-6">
          <div class="max-w-md panel p-6 text-on-surface">
            <h1 class="font-headline-lg text-headline-lg mb-2">Could not load pulse data</h1>
            <p class="font-body-md text-body-md text-on-surface-variant mb-4">${String(err.message || err)}</p>
            <p class="font-body-sm text-body-sm text-on-surface-variant">Expected files in <code class="text-primary">frontend/public/data/</code>.</p>
          </div>
        </div>`;
      return;
    }
  }

  const route = currentRoute();
  if (!window.location.hash) {
    window.location.hash = "#/overview";
  }

  const contentHtml = renderView(route, data);
  app.innerHTML = renderShell({ route, data, contentHtml });
  bindShellEvents();
  syncThemeControls(app);
  if (route === "reviews") bindReviewsFilters(app);
  window.scrollTo({ top: 0, behavior: "auto" });
}

initTheme();
window.addEventListener("hashchange", render);
document.addEventListener("themechange", () => syncThemeControls());
render();
