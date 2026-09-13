/* FairLens — Fairness Lab workflow */
(() => {
  let currentDataset = null; // { dataset_id, name, ...profile }

  const el = (id) => document.getElementById(id);

  function showStatus(node, message, type) {
    node.style.display = "block";
    node.textContent = message;
    node.className = `status-msg ${type}`;
  }

  function renderPreview(profile) {
    el("stat-rows").textContent = profile.row_count.toLocaleString();
    el("stat-cols").textContent = profile.column_count;
    el("stat-missing").textContent = profile.total_missing.toLocaleString();

    const head = el("preview-head");
    const body = el("preview-body");
    head.innerHTML = "";
    body.innerHTML = "";

    profile.columns.forEach((c) => {
      const th = document.createElement("th");
      th.textContent = c;
      head.appendChild(th);
    });

    profile.preview_rows.forEach((row) => {
      const tr = document.createElement("tr");
      profile.columns.forEach((c) => {
        const td = document.createElement("td");
        const v = row[c];
        td.textContent = v === null || v === undefined ? "—" : v;
        tr.appendChild(td);
      });
      body.appendChild(tr);
    });

    el("detected-cols").innerHTML =
      `<strong>${profile.numeric_columns.length}</strong> numeric columns, ` +
      `<strong>${profile.categorical_columns.length}</strong> categorical columns detected.`;

    el("step-preview").hidden = false;
  }

  function populateColumnSelects(profile) {
    const attrSel = el("select-attr");
    const outcomeSel = el("select-outcome");
    const positiveSel = el("select-positive");

    attrSel.innerHTML = "";
    outcomeSel.innerHTML = "";

    const candidates = profile.candidate_attribute_columns.length
      ? profile.candidate_attribute_columns
      : profile.columns;

    candidates.forEach((c) => {
      attrSel.appendChild(new Option(c, c));
      outcomeSel.appendChild(new Option(c, c));
    });

    // sensible defaults for the demo dataset, else just first two candidates
    const defaultAttr = candidates.includes("gender") ? "gender" : candidates[0];
    const defaultOutcome = candidates.includes("approved")
      ? "approved"
      : candidates[candidates.length > 1 ? 1 : 0];

    attrSel.value = defaultAttr;
    outcomeSel.value = defaultOutcome;

    updatePositiveOptions(profile);

    attrSel.onchange = () => updatePositiveOptions(profile);
    outcomeSel.onchange = () => updatePositiveOptions(profile);

    el("step-columns").hidden = false;
    el("btn-run").disabled = false;
  }

  function updatePositiveOptions(profile) {
    const outcomeSel = el("select-outcome");
    const positiveSel = el("select-positive");
    const col = outcomeSel.value;
    const values = (profile.column_unique_values && profile.column_unique_values[col]) || [];
    positiveSel.innerHTML = "";
    if (values.length) {
      values.forEach((v) => positiveSel.appendChild(new Option(v, v)));
      if (values.includes("Yes")) positiveSel.value = "Yes";
    } else {
      const opt = new Option("Enter a value manually below", "");
      positiveSel.appendChild(opt);
    }
  }

  async function loadDemo() {
    const status = el("source-status");
    showStatus(status, "Loading demo dataset…", "info");
    try {
      const profile = await FairLensAPI.getDemoDataset();
      currentDataset = profile;
      showStatus(status, `Loaded "${profile.name}" — ${profile.row_count} rows.`, "info");
      renderPreview(profile);
      populateColumnSelects(profile);
    } catch (err) {
      showStatus(status, `Could not load demo dataset: ${err.message}`, "error");
    }
  }

  async function handleUpload(file) {
    const status = el("source-status");
    showStatus(status, `Uploading ${file.name}…`, "info");
    try {
      const profile = await FairLensAPI.uploadCSV(file);
      currentDataset = profile;
      showStatus(status, `Loaded "${profile.name}" — ${profile.row_count} rows.`, "info");
      renderPreview(profile);
      populateColumnSelects(profile);
    } catch (err) {
      showStatus(status, `Upload failed: ${err.message}`, "error");
    }
  }

  async function runAnalysis() {
    if (!currentDataset) return;
    const status = el("analyze-status");
    const btn = el("btn-run");
    btn.disabled = true;
    btn.textContent = "Running analysis…";
    showStatus(status, "Computing group selection rates, demographic parity, and disparate impact…", "info");

    const payload = {
      dataset_id: currentDataset.dataset_id,
      protected_attribute: el("select-attr").value,
      outcome_column: el("select-outcome").value,
      positive_outcome: el("select-positive").value,
    };

    try {
      const result = await FairLensAPI.analyze(payload);
      sessionStorage.setItem("fairlens_result", JSON.stringify(result));
      sessionStorage.setItem("fairlens_dataset_name", currentDataset.name);
      showStatus(status, "Analysis complete — opening results…", "info");
      setTimeout(() => { window.location.href = "results.html"; }, 500);
    } catch (err) {
      showStatus(status, `Fairness test failed: ${err.message}`, "error");
      btn.disabled = false;
      btn.textContent = "Run Fairness Test";
    }
  }

  document.addEventListener("DOMContentLoaded", () => {
    el("btn-demo").addEventListener("click", loadDemo);
    el("csv-upload").addEventListener("change", (e) => {
      if (e.target.files && e.target.files[0]) handleUpload(e.target.files[0]);
    });
    el("btn-run").addEventListener("click", runAnalysis);
  });
})();
