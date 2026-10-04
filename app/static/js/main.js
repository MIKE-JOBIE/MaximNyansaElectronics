// ─── Flash auto-dismiss ─────────────────────────────
document.addEventListener("DOMContentLoaded", () => {
  setTimeout(() => {
    document.querySelectorAll(".flash").forEach(f => {
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

  if (!toggler) return;
  if (!navMenu) return;

  toggler.addEventListener("click", (e) => {
    e.preventDefault();
    e.stopPropagation();
    navMenu.classList.toggle("open");
    console.log("Menu toggled:", navMenu.classList.contains("open"));
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