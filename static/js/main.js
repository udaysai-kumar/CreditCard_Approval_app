// Meridian front-end interactions
document.addEventListener("DOMContentLoaded", () => {
  initNavbar();
  initNavToggle();
  initScrollReveal();
  initAnimatedCounters();
  initGauges();
  initFormValidation();
  initFormProgress();
  initLoadingOverlay();
  initPasswordControls();
  initButtonLighting();
  initTilt();
  autoDismissFlashes();
});

function initNavbar() {
  const nav = document.getElementById("navbar");
  if (!nav) return;
  const sync = () => nav.classList.toggle("scrolled", window.scrollY > 12);
  sync();
  window.addEventListener("scroll", sync, { passive: true });
}

function initNavToggle() {
  const btn = document.getElementById("navToggle");
  const links = document.getElementById("navLinks");
  if (!btn || !links) return;
  btn.addEventListener("click", () => {
    const open = links.classList.toggle("open");
    btn.setAttribute("aria-expanded", String(open));
    btn.innerHTML = open ? '<i class="fa-solid fa-xmark"></i>' : '<i class="fa-solid fa-bars"></i>';
  });
}

function initScrollReveal() {
  const targets = document.querySelectorAll("[data-aos]");
  if (!targets.length) return;
  const observer = new IntersectionObserver((entries) => {
    entries.forEach((entry) => {
      if (!entry.isIntersecting) return;
      entry.target.classList.add("aos-in");
      observer.unobserve(entry.target);
    });
  }, { threshold: 0.14 });
  targets.forEach((target, index) => {
    target.style.transitionDelay = `${Math.min(index * 35, 180)}ms`;
    observer.observe(target);
  });
}

function initAnimatedCounters() {
  const counters = document.querySelectorAll("[data-counter]");
  if (!counters.length) return;
  const observer = new IntersectionObserver((entries) => {
    entries.forEach((entry) => {
      if (!entry.isIntersecting) return;
      const el = entry.target;
      const target = parseFloat(el.dataset.counter || "0");
      const decimals = parseInt(el.dataset.decimals || "0", 10);
      const start = performance.now();
      const duration = 1300;
      function tick(now) {
        const progress = Math.min((now - start) / duration, 1);
        const eased = 1 - Math.pow(1 - progress, 3);
        const value = target * eased;
        el.textContent = decimals ? value.toFixed(decimals) : Math.round(value).toLocaleString();
        if (progress < 1) requestAnimationFrame(tick);
      }
      requestAnimationFrame(tick);
      observer.unobserve(el);
    });
  }, { threshold: 0.35 });
  counters.forEach((counter) => observer.observe(counter));
}

function initGauges() {
  document.querySelectorAll("[data-gauge]").forEach((svg) => {
    const value = Math.max(0, Math.min(100, parseFloat(svg.dataset.gauge || "0")));
    const fill = svg.querySelector(".gauge-arc-fill");
    if (!fill) return;
    const circumference = parseFloat(fill.dataset.circumference || fill.getTotalLength());
    const offset = circumference - (value / 100) * circumference;
    fill.style.strokeDasharray = circumference;
    fill.style.strokeDashoffset = circumference;
    setTimeout(() => { fill.style.strokeDashoffset = offset; }, 180);
  });
}

function initFormValidation() {
  document.querySelectorAll("form[data-validate]").forEach((form) => {
    form.addEventListener("submit", (e) => {
      let valid = true;
      form.querySelectorAll("[required]").forEach((input) => {
        const field = input.closest(".field");
        if (!field) return;
        let ok = input.value.trim().length > 0;
        if (ok && input.type === "email") ok = /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(input.value.trim());
        if (ok && input.type === "number") {
          const num = parseFloat(input.value);
          const min = input.min !== "" ? parseFloat(input.min) : -Infinity;
          const max = input.max !== "" ? parseFloat(input.max) : Infinity;
          ok = !Number.isNaN(num) && num >= min && num <= max;
        }
        if (ok && input.name === "confirm_password") {
          const password = form.querySelector('[name="password"]');
          ok = !password || input.value === password.value;
        }
        field.classList.toggle("invalid", !ok);
        if (!ok) valid = false;
      });
      if (!valid) {
        e.preventDefault();
        const firstInvalid = form.querySelector(".field.invalid");
        if (firstInvalid) firstInvalid.scrollIntoView({ behavior: "smooth", block: "center" });
        return;
      }
      if (form.dataset.loading !== "false") showLoadingOverlay();
    });
  });
}

function initFormProgress() {
  const bar = document.getElementById("formProgress");
  const form = document.querySelector(".prediction-form");
  if (!bar || !form) return;
  const fields = Array.from(form.querySelectorAll("input, select, textarea")).filter((el) => el.type !== "hidden");
  const update = () => {
    const complete = fields.filter((el) => {
      if (el.type === "checkbox") return el.checked;
      return String(el.value || "").trim().length > 0;
    }).length;
    const percent = Math.max(8, Math.round((complete / fields.length) * 100));
    bar.style.width = `${percent}%`;
  };
  fields.forEach((field) => field.addEventListener("input", update));
  fields.forEach((field) => field.addEventListener("change", update));
  update();
}

function initLoadingOverlay() {
  if (document.getElementById("loadingOverlay")) return;
  const overlay = document.createElement("div");
  overlay.id = "loadingOverlay";
  overlay.className = "loading-overlay";
  overlay.innerHTML = `
    <div class="loading-card">
      <div class="spinner"></div>
      <h3>Scoring application</h3>
      <p>Aligning features, running the promoted model, and preparing the decision summary.</p>
      <div class="loading-bar"><span></span></div>
    </div>`;
  document.body.appendChild(overlay);
}

function showLoadingOverlay() {
  const overlay = document.getElementById("loadingOverlay");
  if (overlay) overlay.classList.add("show");
}

function initPasswordControls() {
  document.querySelectorAll(".password-toggle").forEach((btn) => {
    const field = btn.closest(".field");
    const input = field && field.querySelector("[data-password-input]");
    if (!input) return;
    btn.addEventListener("click", () => {
      const showing = input.type === "text";
      input.type = showing ? "password" : "text";
      btn.setAttribute("aria-label", showing ? "Show password" : "Hide password");
      btn.innerHTML = showing ? '<i class="fa-solid fa-eye"></i>' : '<i class="fa-solid fa-eye-slash"></i>';
    });
  });

  const strengthInput = document.querySelector("[data-password-strength]");
  const meter = document.querySelector(".password-meter span");
  if (!strengthInput || !meter) return;
  strengthInput.addEventListener("input", () => {
    const value = strengthInput.value;
    let score = Math.min(value.length / 10, 1);
    if (/[A-Z]/.test(value)) score += .18;
    if (/[0-9]/.test(value)) score += .18;
    if (/[^A-Za-z0-9]/.test(value)) score += .18;
    score = Math.min(score, 1);
    meter.style.width = `${Math.max(score * 100, value ? 18 : 0)}%`;
    meter.style.background = score > .72 ? "var(--green-600)" : score > .42 ? "var(--amber-600)" : "var(--red-600)";
  });
}

function initButtonLighting() {
  document.querySelectorAll(".btn").forEach((btn) => {
    btn.addEventListener("pointermove", (event) => {
      const rect = btn.getBoundingClientRect();
      btn.style.setProperty("--mx", `${event.clientX - rect.left}px`);
      btn.style.setProperty("--my", `${event.clientY - rect.top}px`);
    });
  });
}

function initTilt() {
  document.querySelectorAll("[data-tilt]").forEach((el) => {
    el.addEventListener("pointermove", (event) => {
      const rect = el.getBoundingClientRect();
      const x = (event.clientX - rect.left) / rect.width - .5;
      const y = (event.clientY - rect.top) / rect.height - .5;
      el.style.transform = `perspective(1200px) rotateX(${y * -4}deg) rotateY(${x * 5}deg)`;
    });
    el.addEventListener("pointerleave", () => {
      el.style.transform = "";
    });
  });
}

function autoDismissFlashes() {
  document.querySelectorAll(".flash").forEach((flash) => {
    setTimeout(() => {
      flash.style.transition = "opacity .35s ease, transform .35s ease";
      flash.style.opacity = "0";
      flash.style.transform = "translateY(-8px)";
      setTimeout(() => flash.remove(), 380);
    }, 5200);
  });
}

function celebrateApproval() {
  const el = document.querySelector(".result-icon.approved");
  if (!el) return;
  el.animate([
    { transform: "scale(.7) rotate(-8deg)", opacity: 0 },
    { transform: "scale(1.08) rotate(4deg)", opacity: 1 },
    { transform: "scale(1) rotate(0)" }
  ], { duration: 700, easing: "cubic-bezier(.2,1.4,.3,1)" });

  for (let i = 0; i < 34; i += 1) {
    const piece = document.createElement("span");
    piece.style.cssText = `
      position:fixed;left:${48 + Math.random() * 8}vw;top:22vh;width:7px;height:12px;
      background:${i % 3 === 0 ? "var(--green-600)" : i % 3 === 1 ? "var(--blue-600)" : "var(--purple)"};
      border-radius:3px;z-index:998;pointer-events:none;`;
    document.body.appendChild(piece);
    piece.animate([
      { transform: "translate3d(0,0,0) rotate(0deg)", opacity: 1 },
      { transform: `translate3d(${(Math.random() - .5) * 520}px, ${360 + Math.random() * 220}px, 0) rotate(${Math.random() * 540}deg)`, opacity: 0 }
    ], { duration: 1100 + Math.random() * 700, easing: "cubic-bezier(.16,.84,.34,1)" }).onfinish = () => piece.remove();
  }
}
window.celebrateApproval = celebrateApproval;
