/* MedRemind Care - consultation form: counter, draft autosave, shortcuts, prefill. */
(() => {
  "use strict";
  const form = document.querySelector("#consultation-form");
  const question = document.querySelector("#question");
  const medicine = document.querySelector("#medicine_name");
  const counter = document.querySelector("#question-count");
  if (!form || !question || !counter) return;

  const key = form.dataset.draftKey || "medremind-consultation-draft";
  const store = {
    get() { try { return JSON.parse(window.localStorage.getItem(key) || "null"); } catch (e) { return null; } },
    set(value) { try { window.localStorage.setItem(key, JSON.stringify(value)); } catch (e) { /* storage unavailable */ } },
    clear() { try { window.localStorage.removeItem(key); } catch (e) { /* storage unavailable */ } },
  };

  const updateCount = () => {
    counter.textContent = `${question.value.length.toLocaleString()} / 2,000`;
    counter.classList.toggle("is-near-limit", question.value.length >= 1800);
  };
  const grow = () => {
    question.style.height = "auto";
    question.style.height = `${Math.min(question.scrollHeight + 2, 420)}px`;
  };

  /* Prefill the medicine from ?medicine=Name (used by the catalog's "Ask about this" links) */
  const wanted = new URLSearchParams(window.location.search).get("medicine");
  if (wanted && medicine) {
    const match = Array.from(medicine.options).find((option) => option.value === wanted);
    if (match) { medicine.value = wanted; question.focus(); }
  }

  /* Restore a saved draft (only into empty fields) */
  const draft = store.get();
  if (draft) {
    if (!question.value && draft.question) question.value = draft.question;
    if (medicine && !medicine.value && draft.medicine) medicine.value = draft.medicine;
    if (draft.question) {
      const note = document.createElement("div");
      note.className = "draft-note";
      note.textContent = "Draft restored from your last visit.";
      counter.closest(".question-guidance").after(note);
    }
  }

  const save = () => store.set({ question: question.value, medicine: medicine ? medicine.value : "" });
  question.addEventListener("input", () => { updateCount(); grow(); save(); });
  medicine?.addEventListener("change", save);
  form.addEventListener("submit", () => store.clear());

  /* Ctrl/Cmd + Enter sends the request */
  question.addEventListener("keydown", (event) => {
    if ((event.ctrlKey || event.metaKey) && event.key === "Enter") {
      event.preventDefault();
      form.requestSubmit();
    }
  });

  updateCount();
  grow();
})();
