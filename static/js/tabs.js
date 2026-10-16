/* MedRemind Care - client tabs: highlights the tab for the page and section you are viewing. */
(() => {
  "use strict";
  const bar = document.querySelector("#client-tabs");
  if (!bar) return;
  const tabs = Array.from(bar.querySelectorAll("a[data-tab]"));
  const path = window.location.pathname;
  const onCatalog = path.endsWith("/medicines");
  const onConsult = path.endsWith("/consultations");

  const setActive = (name) => {
    tabs.forEach((tab) => {
      if (tab.dataset.tab === name) tab.setAttribute("aria-current", "page");
      else tab.removeAttribute("aria-current");
    });
  };

  const fromHash = () => {
    const hash = window.location.hash;
    if (onCatalog) return hash === "#medicine-library" ? "medicines" : "overview";
    if (onConsult) return hash === "#my-requests" ? "history" : "new";
    return null;
  };

  const sync = () => { const name = fromHash(); if (name) setActive(name); };
  sync();
  window.addEventListener("hashchange", sync);

  /* Follow the section that is on screen while scrolling */
  const sections = [
    onCatalog && ["medicine-library", "medicines", "overview"],
    onConsult && ["my-requests", "history", "new"],
  ].filter(Boolean)[0];
  if (sections && "IntersectionObserver" in window) {
    const target = document.getElementById(sections[0]);
    if (target) {
      const observer = new IntersectionObserver((entries) => {
        entries.forEach((entry) => setActive(entry.isIntersecting ? sections[1] : sections[2]));
      }, { rootMargin: "-35% 0px -45% 0px" });
      observer.observe(target);
    }
  }

  /* Keep the active tab visible on small screens */
  const current = bar.querySelector('[aria-current="page"]');
  if (current && current.scrollIntoView) current.scrollIntoView({ block: "nearest", inline: "center" });
})();
