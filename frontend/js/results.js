/* FairLens — Results dashboard rendering */
(() => {
  const el = (id) => document.getElementById(id);
  const fmtPct = (v) => `${(v * 100).toFixed(1)}%`;

  function loadResult() {
    const raw = sessionStorage.getItem("fairlens_result");
    if (!raw) return null;
    try { return JSON.parse(raw); } catch (_) { return null; }
  }

  function renderHeader(result, datasetName) {
    el("dataset-name").textContent = datasetName || "Dataset";
    el("score-value").textContent = result.fairness_score.toFixed(1);
    el("score-level").textContent = `${result.bias_level} · ${result.row_count} rows analyzed`;
    el("score-bar").style.width = `${Math.max(2, result.fairness_score)}%`;

    const config = el("config-list");
    config.innerHTML = "";
    const rows = [
      ["Protected attribute", result.protected_attribute],
      ["Outcome column", result.outcome_column],
      ["Positive outcome", result.positive_outcome],
      ["Highest rate group", result.metrics.max_group],
      ["Lowest rate group", result.metrics.min_group],
    ];
    rows.forEach(([label, value]) => {
      const d1 = document.createElement("dt"); d1.textContent = label;
      const d2 = document.createElement("dd"); d2.textContent = value;
      config.appendChild(d1); config.appendChild(d2);
    });
  }

  function renderMetricCards(result) {
    const m = result.metrics;
    const cards = [
      { label: "Selection rate difference", value: `${(m.selection_rate_difference * 100).toFixed(1)} pts`, flag: m.selection_rate_difference > 0.1 },
      { label: "Demographic parity", value: m.demographic_parity.toFixed(2), flag: m.demographic_parity < 0.8 },
      { label: "Disparate impact ratio", value: m.disparate_impact.toFixed(2), flag: !m.passes_four_fifths_rule },
      { label: "Passes four-fifths rule", value: m.passes_four_fifths_rule ? "Yes" : "No", flag: !m.passes_four_fifths_rule },
      { label: "Equal opportunity (TPR)", value: m.equal_opportunity_tpr !== null ? m.equal_opportunity_tpr.toFixed(2) : "Not available", flag: false },
      { label: "Fairness score", value: `${result.fairness_score.toFixed(1)} / 100`, flag: result.fairness_score < 60 },
    ];
    const container = el("metric-cards");
    container.innerHTML = "";
    cards.forEach((c) => {
      const div = document.createElement("div");
      div.className = `panel metric-card ${c.flag ? "flag" : "ok"}`;
      div.innerHTML = `<span class="tag ${c.flag ? "tag-coral" : "tag-lime"}">${c.flag ? "watch" : "ok"}</span>
        <div class="metric-value">${c.value}</div>
        <div class="metric-label">${c.label}</div>`;
      container.appendChild(div);
    });
  }

  function renderGroupTable(result) {
    const body = el("group-table-body");
    body.innerHTML = "";
    result.group_results.forEach((g) => {
      const tr = document.createElement("tr");
      tr.innerHTML = `<td>${g.group}</td><td>${g.count}</td><td>${g.positive_count}</td><td>${fmtPct(g.selection_rate)}</td>`;
      body.appendChild(tr);
    });
  }

  function renderExplanation(result) {
    el("explanation-text").textContent = result.explanation;
    const list = el("recommendations-list");
    list.innerHTML = "";
    result.recommendations.forEach((r) => {
      const li = document.createElement("li");
      li.textContent = r;
      list.appendChild(li);
    });
  }

  const chartPalette = ["#E8593A", "#B9CE2E", "#F17A5C", "#CADB55", "#8FA3B0"];

  function renderCharts(result) {
    const groups = result.group_results;
    const labels = groups.map((g) => g.group);
    const rates = groups.map((g) => +(g.selection_rate * 100).toFixed(1));
    const counts = groups.map((g) => g.count);
    const positives = groups.map((g) => g.positive_count);
    const negatives = groups.map((g) => g.negative_count);

    new Chart(el("chart-approval-rate"), {
      type: "bar",
      data: { labels, datasets: [{ label: "Positive outcome rate (%)", data: rates, backgroundColor: chartPalette }] },
      options: { plugins: { legend: { display: false } }, scales: { y: { beginAtZero: true, max: 100 } } },
    });

    new Chart(el("chart-distribution"), {
      type: "doughnut",
      data: { labels, datasets: [{ data: counts, backgroundColor: chartPalette }] },
      options: { plugins: { legend: { position: "bottom" } } },
    });

    new Chart(el("chart-stacked"), {
      type: "bar",
      data: {
        labels,
        datasets: [
          { label: "Positive", data: positives, backgroundColor: "#B9CE2E" },
          { label: "Negative", data: negatives, backgroundColor: "#E8593A" },
        ],
      },
      options: { plugins: { legend: { position: "bottom" } }, scales: { x: { stacked: true }, y: { stacked: true, beginAtZero: true } } },
    });

    const m = result.metrics;
    new Chart(el("chart-metrics"), {
      type: "bar",
      data: {
        labels: ["Demographic parity", "Disparate impact", "Fairness score (÷100)"],
        datasets: [{
          label: "Value (0–1 scale)",
          data: [m.demographic_parity, m.disparate_impact, result.fairness_score / 100],
          backgroundColor: ["#CADB55", "#F17A5C", "#E8593A"],
        }],
      },
      options: { indexAxis: "y", plugins: { legend: { display: false } }, scales: { x: { min: 0, max: 1 } } },
    });
  }

  async function renderMitigation(result) {
    const m = result.metrics;
    const groups = result.group_results;
    const gA = groups.find((g) => g.group === m.max_group);
    const gB = groups.find((g) => g.group === m.min_group);
    if (!gA || !gB) return;

    try {
      const sim = await FairLensAPI.simulate(gA.selection_rate, gB.selection_rate);

      new Chart(el("chart-mitigation"), {
        type: "bar",
        data: {
          labels: [gA.group, gB.group],
          datasets: [
            { label: "Before", data: [sim.before.group_a_rate * 100, sim.before.group_b_rate * 100], backgroundColor: "#E8593A" },
            { label: "After (simulated)", data: [sim.after.group_a_rate * 100, sim.after.group_b_rate * 100], backgroundColor: "#B9CE2E" },
          ],
        },
        options: { plugins: { legend: { position: "bottom" } }, scales: { y: { beginAtZero: true, max: 100, title: { display: true, text: "Selection rate (%)" } } } },
      });

      const body = el("mitigation-table-body");
      body.innerHTML = `
        <tr><td>Selection rate gap</td><td>${(sim.before.selection_rate_difference * 100).toFixed(1)} pts</td><td>${(sim.after.selection_rate_difference * 100).toFixed(1)} pts</td></tr>
        <tr><td>Disparate impact</td><td>${sim.before.disparate_impact.toFixed(2)}</td><td>${sim.after.disparate_impact.toFixed(2)}</td></tr>
        <tr><td>Fairness score</td><td>${sim.before.fairness_score.toFixed(1)}</td><td>${sim.after.fairness_score.toFixed(1)}</td></tr>
        <tr><td>Bias level</td><td>${sim.before.bias_level}</td><td>${sim.after.bias_level}</td></tr>
      `;
    } catch (err) {
      el("mitigation-table-body").innerHTML = `<tr><td colspan="3">Simulation unavailable: ${err.message}</td></tr>`;
    }
  }

  function downloadReport(result) {
    window.open(FairLensAPI.reportURL(result.dataset_id), "_blank");
  }

  document.addEventListener("DOMContentLoaded", async () => {
    const result = loadResult();
    if (!result) {
      el("no-result-msg").hidden = false;
      return;
    }
    el("results-content").hidden = false;
    const datasetName = sessionStorage.getItem("fairlens_dataset_name");

    renderHeader(result, datasetName);
    renderMetricCards(result);
    renderGroupTable(result);
    renderExplanation(result);
    renderCharts(result);
    await renderMitigation(result);

    el("btn-download").addEventListener("click", () => downloadReport(result));
  });
})();
