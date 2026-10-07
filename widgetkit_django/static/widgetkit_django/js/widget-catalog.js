(() => {
  const payloadNode = document.getElementById("widget-preview-payload");
  const previewEl = document.getElementById("widget-preview");
  const itemButtons = document.querySelectorAll(".wk-catalog-item");
  if (!payloadNode || !previewEl || !itemButtons.length) return;

  const widgetPayload = JSON.parse(payloadNode.textContent || "[]");

  function element(tag, className, text) {
    const node = document.createElement(tag);
    node.className = className;
    if (text !== undefined) node.textContent = text;
    return node;
  }

  function renderPreview(widgetId) {
    const item = widgetPayload.find((entry) => entry.widget_id === widgetId);
    if (!item) return;
    const card = element("div", "wk-catalog-preview-card");
    const head = element("div", "wk-catalog-preview-head");
    head.append(
      element("strong", "", item.label),
      element("code", "", item.widget_id),
    );
    card.append(head);
    const notice = item.note || (item.status !== "sample" ? item.status : "");
    if (notice) card.append(element("p", "wk-catalog-preview-mode", notice));
    const body = element("div", "wk-catalog-preview-body");
    body.setAttribute("inert", "");
    body.setAttribute("aria-label", "Read-only widget sample");
    body.innerHTML = item.body_html || "";
    card.append(body);
    const code = element("pre", "wk-catalog-code", item.body_html || "");
    const source = element("details", "wk-catalog-source");
    source.append(element("summary", "", "Read-only rendered HTML"), code);
    previewEl.replaceChildren(card, element("p", "wk-catalog-muted", item.description), source);

    itemButtons.forEach((button) => {
      const active = button.dataset.widgetId === item.widget_id;
      button.classList.toggle("is-active", active);
      button.setAttribute("aria-pressed", String(active));
    });
  }

  itemButtons.forEach((button) => {
    button.addEventListener("click", () => renderPreview(button.dataset.widgetId));
  });
  if (widgetPayload.length) renderPreview(widgetPayload[0].widget_id);
})();
