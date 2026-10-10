let cache = null;

function dataUrl(path) {
  const base = (import.meta.env.VITE_DATA_BASE || "").replace(/\/$/, "");
  return `${base}${path}`;
}

export async function loadDashboardData() {
  if (cache) return cache;

  const [pulseRes, reviewsRes] = await Promise.all([
    fetch(dataUrl("/data/pulse.json"), { cache: "no-store" }),
    fetch(dataUrl("/data/reviews.json"), { cache: "no-store" }),
  ]);

  if (!pulseRes.ok) throw new Error("Failed to load pulse.json");
  if (!reviewsRes.ok) throw new Error("Failed to load reviews.json");

  const pulse = await pulseRes.json();
  const reviews = await reviewsRes.json();

  const themeById = Object.fromEntries(
    (pulse.themes || []).map((t) => [t.theme_id, t]),
  );

  const actions = (pulse.actions || []).map((action, index) => {
    const theme = themeById[action.theme_id] || {};
    const statuses = ["in_review", "suggested", "done"];
    const priorities = ["P0", "P1", "P1"];
    return {
      ...action,
      priority: priorities[index] || "P2",
      status: statuses[index] || "suggested",
      count: theme.count || 0,
      avg_rating: theme.avg_rating || 0,
      insight: theme.insight || "",
    };
  });

  cache = {
    pulse,
    reviews,
    actions,
    themes: pulse.themes || [],
    quotes: pulse.quotes || [],
  };
  return cache;
}

/** Test helper / HMR-friendly reset */
export function clearDashboardCache() {
  cache = null;
}
