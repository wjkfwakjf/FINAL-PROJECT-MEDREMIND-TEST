/* MedRemind Care - medicine library: search, result count, "/" shortcut. */
(() => {
  "use strict";
  const search = document.querySelector("#medicine-search");
  const cards = Array.from(document.querySelectorAll(".medicine-card"));
  const emptyState = document.querySelector("#medicine-empty");
  const count = document.querySelector("#medicine-count");
  if (!search) return;

  const update = () => {
    const query = search.value.trim().toLowerCase();
    let visible = 0;
    cards.forEach((card) => {
      card.hidden = !card.dataset.search.includes(query);
      if (!card.hidden) visible += 1;
    });
    if (emptyState) emptyState.hidden = visible > 0;
    if (count) {
      count.textContent = query
        ? `${visible} of ${cards.length} medicines match "${search.value.trim()}"`
        : `${cards.length} medicines`;
    }
  };
  search.addEventListener("input", update);

  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && document.activeElement === search) {
      search.value = "";
      update();
      search.blur();
      return;
    }
    if (event.key === "/" && !["INPUT", "TEXTAREA", "SELECT"].includes(document.activeElement.tagName)) {
      event.preventDefault();
      search.focus();
      document.querySelector("#medicine-library")?.scrollIntoView({ behavior: "smooth" });
    }
  });
})();
