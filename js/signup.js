(() => {
  const password = document.getElementById("password");
  const confirm = document.getElementById("confirm_password");
  const meter = document.getElementById("password-meter");
  const hint = document.getElementById("password-hint");
  if (!password || !meter || !hint) return;

  document.querySelectorAll(".password-toggle").forEach((button) => {
    button.addEventListener("click", () => {
      const input = document.getElementById(button.getAttribute("aria-controls"));
      if (!input) return;
      const showPassword = input.type === "password";
      input.type = showPassword ? "text" : "password";
      button.textContent = showPassword ? "Hide" : "Show";
      button.setAttribute("aria-pressed", String(showPassword));
    });
  });

  password.addEventListener("input", () => {
    const value = password.value;
    if (!value) {
      meter.dataset.strength = "0";
      hint.textContent = "Use at least 8 characters.";
      return;
    }
    const checks = [
      value.length >= 8,
      /[a-z]/.test(value) && /[A-Z]/.test(value),
      /\d/.test(value),
      /[^A-Za-z0-9]/.test(value),
    ];
    const strength = checks.filter(Boolean).length;
    meter.dataset.strength = String(strength);
    hint.textContent = [
      "Add more characters for a stronger password.",
      "A little stronger.",
      "Good password strength.",
      "Strong password.",
    ][Math.max(strength - 1, 0)];
  });

  /* Confirm-password match note + Caps Lock warning (additions) */
  if (confirm) {
    const note = document.createElement("small");
    note.className = "field-note";
    note.setAttribute("aria-live", "polite");
    confirm.closest(".password-field").after(note);
    const check = () => {
      if (!confirm.value) { note.textContent = ""; note.className = "field-note"; return; }
      const ok = confirm.value === password.value;
      note.textContent = ok ? "Passwords match." : "Passwords do not match yet.";
      note.className = "field-note " + (ok ? "is-ok" : "is-bad");
    };
    password.addEventListener("input", check);
    confirm.addEventListener("input", check);
  }
  [password, confirm].forEach((input) => {
    input?.addEventListener("keyup", (event) => {
      if (!event.getModifierState) return;
      const on = event.getModifierState("CapsLock");
      let warn = input.closest(".password-field").parentNode.querySelector(".caps-note");
      if (on && !warn) {
        warn = document.createElement("small");
        warn.className = "field-note is-warn caps-note";
        warn.textContent = "Caps Lock is on.";
        input.closest(".password-field").after(warn);
      } else if (!on && warn) warn.remove();
    });
  });
})();
