const STORAGE_KEY = "groww_theme";

export function initTheme() {
  const saved = localStorage.getItem(STORAGE_KEY);
  let mode = "dark";
  if (saved === "light" || saved === "dark") {
    mode = saved;
  } else if (window.matchMedia("(prefers-color-scheme: light)").matches) {
    mode = "light";
  }
  applyTheme(mode, { silent: true });
}

export function applyTheme(mode, { silent = false } = {}) {
  const root = document.documentElement;
  root.classList.toggle("dark", mode !== "light");
  root.dataset.theme = mode;
  localStorage.setItem(STORAGE_KEY, mode);
  if (!silent) {
    document.dispatchEvent(new CustomEvent("themechange", { detail: { mode } }));
  }
}

export function toggleTheme() {
  applyTheme(currentTheme() === "dark" ? "light" : "dark");
}

export function setTheme(mode) {
  applyTheme(mode === "light" ? "light" : "dark");
}

export function currentTheme() {
  return document.documentElement.classList.contains("dark") ? "dark" : "light";
}

export function syncThemeControls(root = document) {
  const mode = currentTheme();
  root.querySelectorAll("[data-theme-option]").forEach((btn) => {
    const active = btn.getAttribute("data-theme-option") === mode;
    btn.setAttribute("aria-pressed", active ? "true" : "false");
  });
}
