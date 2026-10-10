import { badge, escapeHtml, formatDate, icon } from "../utils.js";

export function renderDelivery({ pulse }) {
  const email = pulse.email || {};
  const docsOk = Boolean(pulse.document_id || pulse.doc_url);
  const mailOk = email.status === "sent";

  return `
    <section class="flex flex-col gap-space-xl">
      <header class="flex flex-col gap-space-xs">
        <div class="flex flex-wrap items-center gap-space-sm">
          ${badge("MCP delivery", "primary")}
          ${mailOk && docsOk ? badge("Live", "success") : badge("Check status", "warning")}
        </div>
        <h1 class="font-display-lg text-display-lg text-on-surface tracking-tight">Delivery</h1>
        <p class="font-body-md text-body-md text-on-surface-variant max-w-3xl">
          Google Docs append and Gmail send status for week ending ${escapeHtml(formatDate(pulse.week_ending))}.
        </p>
      </header>

      <div class="grid grid-cols-1 lg:grid-cols-2 gap-space-md">
        ${deliveryCard({
          title: "Google Docs",
          iconName: "description",
          ok: docsOk,
          statusLabel: docsOk ? "Appended" : "Pending",
          rows: [
            ["Document ID", pulse.document_id || "—"],
            ["Request ID", pulse.docs_request_id || "—"],
            ["Doc URL", pulse.doc_url || "—"],
          ],
          cta: pulse.doc_url
            ? `<a href="${escapeHtml(pulse.doc_url)}" target="_blank" rel="noopener" class="inline-flex items-center gap-space-xs px-space-md py-2 rounded-lg bg-primary-container text-on-primary-container font-label-md text-label-md hover:brightness-110 transition-all">
                ${icon("open_in_new", "text-[16px]")} Open Doc
              </a>`
            : "",
        })}

        ${deliveryCard({
          title: "Gmail",
          iconName: "mail",
          ok: mailOk,
          statusLabel: email.status || "unknown",
          rows: [
            ["Recipient", email.recipient || "—"],
            ["Request ID", email.request_id || "—"],
            ["Message ID", email.message_id || "—"],
            ["Thread ID", email.thread_id || "—"],
          ],
        })}
      </div>

      <div class="panel panel-static p-space-lg flex flex-col gap-space-md">
        <div class="flex items-center gap-space-sm">
          ${icon("hub", "text-[22px] text-primary")}
          <h2 class="font-headline-md text-headline-md text-on-surface">Pipeline metadata</h2>
        </div>
        <div class="grid grid-cols-1 md:grid-cols-3 gap-space-md">
          ${meta("Week ending", formatDate(pulse.week_ending))}
          ${meta("Window", `${pulse.window_weeks} weeks`)}
          ${meta("Source fixture", pulse.source_fixture || "live export")}
          ${meta("Word count", String(pulse.word_count ?? "—"))}
          ${meta("Soft fail", pulse.soft_fail_note || "None")}
          ${meta("Product", pulse.product_name || "Groww")}
        </div>
      </div>
    </section>`;
}

function deliveryCard({ title, iconName, ok, statusLabel, rows, cta = "" }) {
  return `
    <article class="panel p-space-lg flex flex-col gap-space-md">
      <div class="flex items-center justify-between gap-space-sm">
        <div class="flex items-center gap-space-sm">
          <span class="p-2 rounded-lg bg-surface-container text-primary">${icon(iconName, "text-[20px]")}</span>
          <h2 class="font-headline-md text-headline-md text-on-surface">${escapeHtml(title)}</h2>
        </div>
        ${badge(statusLabel, ok ? "success" : "warning")}
      </div>
      <dl class="flex flex-col gap-space-sm">
        ${rows
          .map(
            ([k, v]) => `
          <div class="flex flex-col gap-0.5 p-space-sm rounded-lg bg-surface-container">
            <dt class="font-label-sm text-label-sm text-on-surface-variant">${escapeHtml(k)}</dt>
            <dd class="font-code-tabular text-code-tabular text-on-surface break-all">${escapeHtml(v)}</dd>
          </div>`,
          )
          .join("")}
      </dl>
      ${cta}
    </article>`;
}

function meta(label, value) {
  return `
    <div class="p-space-md rounded-lg bg-surface-container">
      <div class="font-label-sm text-label-sm text-on-surface-variant">${escapeHtml(label)}</div>
      <div class="mt-1 font-body-md text-body-md text-on-surface break-all">${escapeHtml(value)}</div>
    </div>`;
}
