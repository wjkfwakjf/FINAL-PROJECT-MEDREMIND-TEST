/* MedRemind Care - admin dashboard: live alerts, request filters, search. */
(() => {
  "use strict";
  const notice = document.querySelector("#consultation-notice");
  const status = document.querySelector("#notification-connection");
  const alertButton = document.querySelector("#enable-browser-notifications");
  const baseTitle = document.title;
  let lastId = notice ? Number(notice.dataset.afterId) || 0 : 0;
  let newCount = 0;

  const showNew = (item) => {
    newCount += 1;
    notice.hidden = false;
    document.querySelector("#consultation-notice-title").textContent =
      `${newCount} new consultation${newCount === 1 ? "" : "s"}`;
    document.querySelector("#consultation-notice-message").textContent =
      `${item.full_name} (@${item.username}) asked about ${item.medicine_name}. Refresh the dashboard to review the full request.`;
    document.title = `(${newCount}) ${baseTitle}`;
    if ("Notification" in window && Notification.permission === "granted") {
      new Notification("MedRemind Care: new consultation", {
        body: `${item.full_name} asked about ${item.medicine_name}.`,
      });
    }
  };

  const setStatus = (text, offline) => {
    if (!status) return;
    status.textContent = text;
    status.classList.toggle("is-offline", Boolean(offline));
  };

  const check = async () => {
    if (!notice || document.hidden) return;
    try {
      const response = await fetch(`${notice.dataset.notificationsUrl}?after_id=${lastId}`, {
        credentials: "same-origin",
        cache: "no-store",
      });
      if (!response.ok) throw new Error(`Notification check failed (${response.status}).`);
      const result = await response.json();
      result.notifications.forEach((item) => {
        lastId = Math.max(lastId, Number(item.id));
        showNew(item);
      });
      setStatus("Live alerts on", false);
    } catch (error) {
      setStatus("Live alerts unavailable", true);
      console.error("Unable to check for new consultation requests.", error);
    }
  };

  if (notice && status) {
    window.setInterval(check, 8000);
    document.addEventListener("visibilitychange", () => { if (!document.hidden) check(); });
  }

  alertButton?.addEventListener("click", async () => {
    if (!("Notification" in window)) { setStatus("Browser alerts are not supported", true); return; }
    const permission = await Notification.requestPermission();
    alertButton.textContent = permission === "granted" ? "Browser alerts enabled" : "Browser alerts blocked";
    if (permission === "denied") setStatus("Allow notifications in browser settings to enable alerts", true);
  });

  /* Consultation search + status filter */
  const search = document.querySelector("#consultation-search");
  const rows = Array.from(document.querySelectorAll("#consultation-rows tr"));
  const empty = document.querySelector("#consultation-empty");
  const filters = Array.from(document.querySelectorAll("[data-status-filter]"));
  let activeStatus = "all";

  const update = () => {
    const query = (search?.value || "").trim().toLowerCase();
    let visible = 0;
    rows.forEach((row) => {
      const hit = row.dataset.search.includes(query) && (activeStatus === "all" || row.dataset.status === activeStatus);
      row.hidden = !hit;
      if (hit) visible += 1;
    });
    if (empty) empty.hidden = visible > 0;
  };
  search?.addEventListener("input", update);
  filters.forEach((filter) => {
    filter.addEventListener("click", () => {
      activeStatus = filter.dataset.statusFilter;
      filters.forEach((item) => {
        const on = item === filter;
        item.classList.toggle("is-active", on);
        item.setAttribute("aria-pressed", String(on));
      });
      update();
    });
  });

  /* Account search */
  const accountSearch = document.querySelector("#account-search");
  const accountRows = Array.from(document.querySelectorAll("#account-rows tr"));
  const accountEmpty = document.querySelector("#account-empty");
  accountSearch?.addEventListener("input", () => {
    const query = accountSearch.value.trim().toLowerCase();
    let visible = 0;
    accountRows.forEach((row) => {
      row.hidden = !row.dataset.search.includes(query);
      if (!row.hidden) visible += 1;
    });
    if (accountEmpty) accountEmpty.hidden = visible > 0;
  });

  /* Press "/" to jump to the request search */
  document.addEventListener("keydown", (event) => {
    if (event.key !== "/" || event.metaKey || event.ctrlKey || event.altKey) return;
    if (["INPUT", "TEXTAREA", "SELECT"].includes(document.activeElement.tagName)) return;
    if (!search) return;
    event.preventDefault();
    search.focus();
  });
})();
