/* FairLens — Bias Simulator */
(() => {
  const el = (id) => document.getElementById(id);
  let chart = null;
  let debounceTimer = null;

  function buildChart(rateA, rateB) {
    if (chart) chart.destroy();
    chart = new Chart(el("chart-sim"), {
      type: "bar",
      data: {
        labels: ["Group A", "Group B"],
        datasets: [{
          label: "Selection rate (%)",
          data: [rateA, rateB],
          backgroundColor: ["#E8593A", "#B9CE2E"],
        }],
      },
      options: {
        plugins: { legend: { display: false } },
        scales: { y: { beginAtZero: true, max: 100 } },
      },
    });
  }

  async function update() {
    const a = +el("slider-a").value;
    const b = +el("slider-b").value;
    el("value-a").textContent = `${a}%`;
    el("value-b").textContent = `${b}%`;

    if (!chart) buildChart(a, b);
    else { chart.data.datasets[0].data = [a, b]; chart.update(); }

    const status = el("sim-status");
    status.textContent = "Calculating…";

    try {
      const sim = await FairLensAPI.simulate(a / 100, b / 100);
      status.style.display = "none";

      el("sim-diff").textContent = `${(sim.before.selection_rate_difference * 100).toFixed(1)} percentage points`;
      el("sim-impact").textContent = sim.before.disparate_impact.toFixed(2);
      el("sim-passes").textContent = sim.before.disparate_impact >= 0.8 ? "Yes" : "No";
      el("sim-score").textContent = `${sim.before.fairness_score.toFixed(1)} / 100 — ${sim.before.bias_level}`;

      const band = el("sim-band");
      band.textContent = sim.before.bias_level;
      band.className = `sim-status-band ${sim.before.fairness_score >= 80 ? "ok" : ""}`;
    } catch (err) {
      status.style.display = "block";
      status.className = "status-msg error";
      status.textContent = `Backend unreachable: ${err.message}`;
    }
  }

  function debouncedUpdate() {
    clearTimeout(debounceTimer);
    debounceTimer = setTimeout(update, 120);
  }

  document.addEventListener("DOMContentLoaded", () => {
    el("slider-a").addEventListener("input", debouncedUpdate);
    el("slider-b").addEventListener("input", debouncedUpdate);
    update();
  });
})();
