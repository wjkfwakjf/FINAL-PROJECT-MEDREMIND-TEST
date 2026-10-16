/* MedRemind Care - global behaviour: mobile menu, flash messages, scroll effects,
   show/hide password, double-submit protection. No dependencies. */
(() => {
  "use strict";
  const root = document.documentElement;
  const reduceMotion = window.matchMedia ? window.matchMedia("(prefers-reduced-motion: reduce)").matches : false;

  /* Header shadow while scrolling */
  const onScroll = () => root.classList.toggle("is-scrolled", window.scrollY > 8);
  window.addEventListener("scroll", onScroll, { passive: true });
  onScroll();

  /* Mobile navigation */
  const toggle = document.querySelector(".nav-toggle");
  const nav = document.querySelector("header nav");
  if (toggle && nav) {
    const setOpen = (open) => {
      nav.classList.toggle("is-open", open);
      toggle.setAttribute("aria-expanded", String(open));
    };
    toggle.addEventListener("click", () => setOpen(!nav.classList.contains("is-open")));
    document.addEventListener("keydown", (event) => {
      if (event.key === "Escape") setOpen(false);
    });
    nav.addEventListener("click", (event) => {
      if (event.target.closest("a")) setOpen(false);
    });
  }

  /* Flash messages: close button + auto-dismiss for success */
  document.querySelectorAll(".flash").forEach((flash) => {
    const text = document.createElement("span");
    text.className = "flash-text";
    while (flash.firstChild) text.appendChild(flash.firstChild);
    flash.appendChild(text);
    flash.setAttribute("role", flash.classList.contains("error") ? "alert" : "status");

    const dismiss = () => {
      flash.classList.add("is-leaving");
      window.setTimeout(() => flash.remove(), reduceMotion ? 0 : 300);
    };
    const close = document.createElement("button");
    close.type = "button";
    close.className = "flash-close";
    close.setAttribute("aria-label", "Dismiss message");
    close.textContent = "\u00d7";
    close.addEventListener("click", dismiss);
    flash.appendChild(close);
    if (!flash.classList.contains("error")) window.setTimeout(dismiss, 7000);
  });

  /* Scroll reveal */
  const revealSelector = [
    ".card", ".feature-card", ".medicine-card", ".admin-metric", ".client-quick-card",
    ".problem-grid article", ".benefit-grid article", ".method-step", ".scope-card",
    ".specific-objectives li", ".consultation", ".erd-entity",
  ].join(",");
  const targets = Array.from(document.querySelectorAll(revealSelector));
  if (targets.length && "IntersectionObserver" in window && !reduceMotion) {
    const observer = new IntersectionObserver((entries) => {
      entries.forEach((entry) => {
        if (!entry.isIntersecting) return;
        entry.target.classList.add("is-visible");
        observer.unobserve(entry.target);
      });
    }, { rootMargin: "0px 0px -6% 0px", threshold: 0.08 });
    targets.forEach((el, index) => {
      el.classList.add("reveal");
      el.style.setProperty("--reveal-delay", `${Math.min(index % 6, 5) * 45}ms`);
      observer.observe(el);
    });
  }

  /* Show / hide password on pages that do not have their own toggle */
  document.querySelectorAll('input[type="password"]').forEach((input) => {
    if (input.closest(".password-field") || input.closest(".pw-field") || input.closest(".account-reset")) return;
    const wrap = document.createElement("div");
    wrap.className = "pw-field";
    input.parentNode.insertBefore(wrap, input);
    wrap.appendChild(input);
    const button = document.createElement("button");
    button.type = "button";
    button.className = "pw-toggle";
    button.textContent = "Show";
    button.setAttribute("aria-label", "Show password");
    button.addEventListener("click", () => {
      const show = input.type === "password";
      input.type = show ? "text" : "password";
      button.textContent = show ? "Hide" : "Show";
      button.setAttribute("aria-label", show ? "Hide password" : "Show password");
    });
    wrap.appendChild(button);
  });

  /* Prevent double submits and show progress */
  document.querySelectorAll('form[method="post"]').forEach((form) => {
    form.addEventListener("submit", () => {
      const button = form.querySelector('button[type="submit"].primary');
      if (!button || button.disabled) return;
      window.setTimeout(() => {
        button.disabled = true;
        button.classList.add("is-loading");
      }, 0);
    });
  });
  window.addEventListener("pageshow", () => {
    document.querySelectorAll("button.primary.is-loading").forEach((button) => {
      button.disabled = false;
      button.classList.remove("is-loading");
    });
  });
})();
