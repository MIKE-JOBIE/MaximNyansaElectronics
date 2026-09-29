document.addEventListener("DOMContentLoaded", () => {
  setTimeout(() => document.querySelectorAll(".flash").forEach(f => {
    f.style.transition = "opacity .4s"; f.style.opacity = 0;
    setTimeout(() => f.remove(), 400);
  }), 5000);
  const navToggle = document.querySelector(".navbar-toggler");
  const navCollapse = document.getElementById("nav");
  if (navToggle && navCollapse) navToggle.addEventListener("click", () => navCollapse.classList.toggle("open"));
});