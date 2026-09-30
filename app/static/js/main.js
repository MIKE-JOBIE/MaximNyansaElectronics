document.addEventListener("DOMContentLoaded", () => {
  setTimeout(() => document.querySelectorAll(".flash").forEach(f => {
    f.style.transition = "opacity .4s"; f.style.opacity = 0;
    setTimeout(() => f.remove(), 400);
  }), 5000);
  const navToggle = document.querySelector(".navbar-toggler");
  const navCollapse = document.getElementById("nav");
  if (navToggle && navCollapse) navToggle.addEventListener("click", () => navCollapse.classList.toggle("open"));
});

// Reveal on scroll
document.addEventListener("DOMContentLoaded", () => {
  const els = document.querySelectorAll(".mn-card, .kpi, .section-head");
  if (!els.length) return;
  els.forEach(el => el.classList.add("reveal"));
  const io = new IntersectionObserver(entries => {
    entries.forEach(e => {
      if (e.isIntersecting) { e.target.classList.add("in"); io.unobserve(e.target); }
    });
  }, { threshold: 0.12 });
  els.forEach(el => io.observe(el));
});