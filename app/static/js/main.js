// ─── Flash auto-dismiss ─────────────────────────────
// Success/info auto-hide after 5s; errors/warnings stay until dismissed.
document.addEventListener("DOMContentLoaded", () => {
  setTimeout(() => {
    document.querySelectorAll(".flash").forEach(f => {
      if (f.classList.contains("flash-danger") || f.classList.contains("flash-warning")) return;
      f.style.transition = "opacity .4s";
      f.style.opacity = 0;
      setTimeout(() => f.remove(), 400);
    });
  }, 5000);
});

// ─── Mobile navbar toggle (SINGLE handler) ──────────
document.addEventListener("DOMContentLoaded", () => {
  const toggler = document.querySelector(".mn-navbar .navbar-toggler");
  const navMenu = document.getElementById("nav");

  if (!toggler || !navMenu) return;

  toggler.addEventListener("click", (e) => {
    e.preventDefault();
    e.stopPropagation();
    navMenu.classList.toggle("open");
    toggler.setAttribute("aria-expanded", navMenu.classList.contains("open"));
  });

  // Close the menu when a nav-link is clicked (mobile UX)
  navMenu.querySelectorAll("a").forEach(link => {
    link.addEventListener("click", () => {
      if (window.innerWidth <= 1320) {
        navMenu.classList.remove("open");
        toggler.setAttribute("aria-expanded", "false");
      }
    });
  });
});

// ─── Reveal on scroll (fade-in) ─────────────────────
document.addEventListener("DOMContentLoaded", () => {
  const els = document.querySelectorAll(".mn-card, .kpi, .section-head");
  if (!els.length) return;
  els.forEach(el => el.classList.add("reveal"));

  if (!("IntersectionObserver" in window)) {
    els.forEach(el => el.classList.add("in"));
    return;
  }

  const io = new IntersectionObserver(entries => {
    entries.forEach(e => {
      if (e.isIntersecting) {
        e.target.classList.add("in");
        io.unobserve(e.target);
      }
    });
  }, { threshold: 0.12 });

  els.forEach(el => io.observe(el));
});

// ─── Cart quantity updater (used in cart.html forms) ────
function updateQty(pid, qty) {
  const input = document.getElementById("qty-" + pid);
  const form = document.getElementById("qty-form-" + pid);
  if (input) input.value = qty;
  if (form) form.submit();
}