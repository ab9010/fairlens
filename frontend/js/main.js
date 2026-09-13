/* FairLens — shared nav behavior, runs on every page */
document.addEventListener("DOMContentLoaded", () => {
  const toggle = document.querySelector(".nav-toggle");
  const links = document.querySelector(".nav-links");
  if (toggle && links) {
    toggle.addEventListener("click", () => {
      const open = links.classList.toggle("open");
      toggle.setAttribute("aria-expanded", open ? "true" : "false");
    });
  }

  // Mark the current page's nav link active
  const here = window.location.pathname.split("/").pop() || "index.html";
  document.querySelectorAll(".nav-links a").forEach((a) => {
    const href = a.getAttribute("href");
    if (href === here) a.classList.add("active");
  });

  // Backend connectivity indicator, if the page has one
  const indicator = document.querySelector("[data-api-status]");
  if (indicator && window.FairLensAPI) {
    FairLensAPI.health()
      .then(() => {
        indicator.textContent = "Backend connected";
        indicator.classList.add("tag-lime");
      })
      .catch(() => {
        indicator.textContent = "Backend offline — start the FastAPI server";
        indicator.classList.add("tag-coral");
      });
  }
});
