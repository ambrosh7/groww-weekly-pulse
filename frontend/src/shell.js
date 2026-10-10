import { currentTheme, setTheme, syncThemeControls } from "./theme.js";
import { escapeHtml, formatWeekLabel, icon } from "./utils.js";

const NAV = [
  { id: "overview", label: "Overview", icon: "dashboard" },
  { id: "themes", label: "Themes", icon: "layers", badgeKey: "themes" },
  { id: "quotes", label: "Quotes", icon: "format_quote", badgeKey: "quotes" },
  { id: "actions", label: "Actions", icon: "check_circle", badgeKey: "actions" },
  { id: "reviews", label: "Reviews", icon: "filter_list" },
  { id: "delivery", label: "Delivery", icon: "cloud_done", badgeKey: "delivery" },
];

export function renderShell({ route, data, contentHtml }) {
  const { pulse, themes, quotes, actions } = data;
  const weekLabel = formatWeekLabel(pulse.week_ending);
  const range = `${formatShort(pulse.window_start)} – ${formatShort(pulse.window_end)}`;
  const theme = currentTheme();

  const badges = {
    themes: `${themes.length} Active`,
    quotes: String(quotes.length),
    actions: `${actions.filter((a) => a.status !== "done").length} Pending`,
    delivery: pulse.email?.status === "sent" ? "Live" : "Pending",
  };

  const navItems = NAV.map((item) => {
    const active = item.id === route;
    const badge = item.badgeKey
      ? `<span class="px-space-sm py-0.5 rounded-full ${
          item.badgeKey === "delivery" && badges.delivery === "Live"
            ? "bg-primary/20 text-primary"
            : item.badgeKey === "actions"
              ? "bg-surface-container-highest text-tertiary"
              : "bg-surface-container-highest text-primary"
        } font-label-sm text-label-sm">${escapeHtml(badges[item.badgeKey])}</span>`
      : "";
    return `
      <a href="#/${item.id}" data-nav="${item.id}"${active ? ' aria-current="page"' : ""}
         class="nav-link flex items-center justify-between px-space-md py-space-sm rounded-lg transition-all ${
           active
             ? "bg-primary-container text-on-primary-container font-headline-sm"
             : "text-on-surface-variant hover:bg-surface-container-high hover:text-on-surface"
         }">
        <div class="flex items-center gap-space-sm">
          ${icon(item.icon, "text-[20px]")}
          <span class="font-body-md text-body-md">${item.label}</span>
        </div>
        ${badge}
      </a>`;
  }).join("");

  const tabStrip = NAV.map((item) => {
    const active = item.id === route;
    return `
      <a href="#/${item.id}" class="shrink-0 px-3 py-1.5 rounded-lg font-label-md text-label-md transition-colors ${
        active
          ? "bg-primary-container text-on-primary-container"
          : "text-on-surface-variant hover:bg-surface-container hover:text-on-surface"
      }">${item.label}</a>`;
  }).join("");

  return `
    <aside id="desktop-nav" class="shell-aside hidden lg:flex fixed left-0 top-0 h-full w-72 z-50 flex-col justify-between border-r">
      ${brandBlock()}
      <nav class="flex flex-col gap-space-xs px-space-md flex-1 overflow-y-auto">${navItems}</nav>
      ${footerBlock(pulse)}
    </aside>

    <div id="mobile-backdrop" class="fixed inset-0 z-40 bg-black/40 backdrop-blur-sm opacity-0 pointer-events-none transition-opacity lg:hidden"></div>
    <aside id="mobile-nav" class="fixed left-0 top-0 h-full w-72 z-50 flex flex-col justify-between border-r border-outline-variant/30 -translate-x-full transition-transform duration-200 lg:hidden">
      ${brandBlock(true)}
      <nav class="flex flex-col gap-space-xs px-space-md flex-1 overflow-y-auto">${navItems}</nav>
      ${footerBlock(pulse)}
    </aside>

    <div class="lg:pl-72 min-h-screen">
      <header class="shell-header fixed top-0 left-0 lg:left-72 right-0 z-40 border-b backdrop-blur-xl">
        <div class="h-16 flex items-center justify-between px-space-md lg:px-space-xl">
          <div class="flex items-center gap-space-sm min-w-0">
            <button id="menu-toggle" type="button" class="lg:hidden p-2 rounded-lg bg-surface-container text-on-surface-variant hover:text-on-surface" aria-label="Open menu">
              ${icon("menu", "text-[20px]")}
            </button>
            <div class="flex items-center gap-space-xs font-label-md text-label-md text-on-surface-variant truncate">
              <span class="text-on-surface font-semibold truncate">Groww Weekly Review Pulse</span>
              ${icon("chevron_right", "text-[16px] shrink-0")}
              <span class="text-primary font-medium capitalize">${escapeHtml(route)}</span>
            </div>
          </div>
          <div class="flex items-center gap-space-sm lg:gap-space-md">
            <div class="hidden md:flex items-center gap-space-xs px-space-md py-1.5 rounded-lg bg-surface-container text-on-surface font-label-md text-label-md">
              ${icon("calendar_today", "text-[16px] text-on-surface-variant")}
              <span class="text-on-surface font-medium">${escapeHtml(weekLabel)}</span>
              <span class="hidden xl:inline text-on-surface-variant font-label-sm text-label-sm">(${escapeHtml(range)})</span>
            </div>
            <div class="theme-switch" role="group" aria-label="Color theme">
              <button type="button" data-theme-option="light" aria-pressed="${theme === "light"}" title="Light theme">
                ${icon("light_mode", "text-[16px]")}
              </button>
              <button type="button" data-theme-option="dark" aria-pressed="${theme === "dark"}" title="Dark theme">
                ${icon("dark_mode", "text-[16px]")}
              </button>
            </div>
            <div class="w-8 h-8 rounded-full bg-primary flex items-center justify-center">
              ${icon("person", "text-on-primary text-[18px]")}
            </div>
          </div>
        </div>
        <div class="lg:hidden px-space-md pb-2 overflow-x-auto">
          <div class="inline-flex items-center gap-1 p-1 rounded-xl bg-surface-container border border-outline-variant/40">
            ${tabStrip}
          </div>
        </div>
      </header>

      <main id="main-content" class="shell-main relative pt-[7.25rem] lg:pt-16 min-h-screen w-full px-space-md lg:px-space-xl py-space-xl">
        <div class="view-enter max-w-[1400px]">
          ${contentHtml}
        </div>
      </main>
    </div>`;
}

function brandBlock(withClose = false) {
  return `
    <div class="p-space-lg flex items-center justify-between gap-space-sm">
      <div class="flex items-center gap-space-sm min-w-0">
        <div class="w-9 h-9 rounded-lg bg-primary-container text-on-primary-container font-headline-sm flex items-center justify-center font-bold shrink-0 shadow-sm">G</div>
        <div class="flex flex-col min-w-0">
          <span class="font-headline-sm text-headline-sm text-on-surface tracking-tight truncate">Groww</span>
          <span class="px-space-sm py-0.5 rounded-full bg-surface-container-high text-primary font-label-sm text-label-sm w-fit">Weekly Pulse</span>
        </div>
      </div>
      ${
        withClose
          ? `<button id="menu-close" type="button" class="p-1 text-on-surface-variant hover:text-on-surface" aria-label="Close menu">${icon("close", "text-[20px]")}</button>`
          : ""
      }
    </div>
    <div class="mx-space-lg mb-space-md p-space-sm rounded-lg bg-surface-container flex items-center gap-space-xs text-on-surface-variant font-label-sm text-label-sm">
      ${icon("storefront", "text-[16px] text-primary")}
      <span>Google Play Store · Stocks &amp; MF</span>
    </div>`;
}

function footerBlock(pulse) {
  return `
    <div class="p-space-lg flex flex-col gap-space-md border-t border-outline-variant/30">
      <div class="p-space-sm rounded-lg bg-surface-container flex flex-col gap-space-xs">
        <div class="flex items-center justify-between font-label-sm text-label-sm text-on-surface-variant">
          <span>Sync Window</span>
          <span class="text-primary font-label-md text-label-md">Live Feed</span>
        </div>
        <p class="font-body-sm text-body-sm text-on-surface">Last ${pulse.window_weeks} wks (${pulse.review_count} reviews)</p>
      </div>
      <div class="flex items-center gap-space-sm">
        <div class="relative">
          <div class="w-8 h-8 rounded-full bg-surface-container-highest flex items-center justify-center font-label-md text-label-md text-on-surface">PC</div>
          <span class="absolute bottom-0 right-0 w-2.5 h-2.5 rounded-full bg-primary"></span>
        </div>
        <div class="flex flex-col">
          <span class="font-body-sm text-body-sm font-semibold text-on-surface">Product Core Team</span>
          <span class="font-label-sm text-label-sm text-on-surface-variant">Executive Reviewer</span>
        </div>
      </div>
    </div>`;
}

function formatShort(iso) {
  if (!iso) return "—";
  const d = new Date(`${iso}T00:00:00`);
  return d.toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
}

export function bindShellEvents() {
  document.querySelectorAll("[data-theme-option]").forEach((btn) => {
    btn.addEventListener("click", () => {
      setTheme(btn.getAttribute("data-theme-option"));
      syncThemeControls();
    });
  });

  const backdrop = document.getElementById("mobile-backdrop");
  const mobileNav = document.getElementById("mobile-nav");
  const open = () => {
    mobileNav?.classList.add("open");
    backdrop?.classList.add("open");
  };
  const close = () => {
    mobileNav?.classList.remove("open");
    backdrop?.classList.remove("open");
  };

  document.getElementById("menu-toggle")?.addEventListener("click", open);
  document.getElementById("menu-close")?.addEventListener("click", close);
  backdrop?.addEventListener("click", close);
  document.querySelectorAll("#mobile-nav [data-nav]").forEach((el) => {
    el.addEventListener("click", close);
  });
}
