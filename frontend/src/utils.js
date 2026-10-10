export function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

export function formatDate(iso) {
  if (!iso) return "—";
  const d = new Date(`${iso}T00:00:00`);
  return d.toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

export function formatWeekLabel(iso) {
  return `Week ending: ${formatDate(iso)}`;
}

export function stars(rating) {
  const n = Math.max(0, Math.min(5, Number(rating) || 0));
  return "★".repeat(n) + "☆".repeat(5 - n);
}

export function avgRating(reviews) {
  if (!reviews.length) return 0;
  const sum = reviews.reduce((acc, r) => acc + Number(r.rating || 0), 0);
  return sum / reviews.length;
}

export function pct(part, whole) {
  if (!whole) return 0;
  return Math.round((part / whole) * 1000) / 10;
}

export function icon(name, className = "text-[20px]") {
  return `<span class="material-symbols-outlined ${className}">${name}</span>`;
}

export function badge(text, tone = "neutral") {
  const tones = {
    neutral: "bg-surface-container-highest text-on-surface-variant",
    primary: "bg-primary/15 text-primary",
    warning: "bg-tertiary/15 text-tertiary",
    danger: "bg-error/15 text-error",
    success: "bg-primary/20 text-primary",
  };
  return `<span class="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full font-label-sm text-label-sm ${tones[tone] || tones.neutral}">${escapeHtml(text)}</span>`;
}

export function ratingTone(rating) {
  if (rating < 2) return "danger";
  if (rating < 3) return "warning";
  return "primary";
}

/** Compact SVG sparkline from numeric series (0–n). */
export function sparkline(values, { width = 120, height = 36, color = "var(--accent)" } = {}) {
  const nums = values.map(Number).filter((n) => Number.isFinite(n));
  if (nums.length < 2) {
    return `<svg class="sparkline" width="${width}" height="${height}" viewBox="0 0 ${width} ${height}" aria-hidden="true"></svg>`;
  }
  const min = Math.min(...nums);
  const max = Math.max(...nums);
  const span = max - min || 1;
  const step = width / (nums.length - 1);
  const pts = nums.map((v, i) => {
    const x = i * step;
    const y = height - ((v - min) / span) * (height - 4) - 2;
    return [x, y];
  });
  const line = pts.map(([x, y], i) => `${i === 0 ? "M" : "L"}${x.toFixed(1)},${y.toFixed(1)}`).join(" ");
  const area = `${line} L${width},${height} L0,${height} Z`;
  return `
    <svg class="sparkline" width="${width}" height="${height}" viewBox="0 0 ${width} ${height}" aria-hidden="true">
      <path class="fill" d="${area}" style="fill:${color}"></path>
      <path d="${line}" style="stroke:${color}"></path>
    </svg>`;
}
