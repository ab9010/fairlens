/* FairLens — shared API client */
const FairLensAPI = (() => {
  const BASE = "http://localhost:8000/api";

  async function handle(res) {
    let body;
    try { body = await res.json(); } catch (_) { body = null; }
    if (!res.ok) {
      const msg = (body && body.detail) ? body.detail : `Request failed (${res.status})`;
      throw new Error(msg);
    }
    return body;
  }

  return {
    async health() {
      const res = await fetch(`${BASE}/health`);
      return handle(res);
    },
    async getDemoDataset() {
      const res = await fetch(`${BASE}/demo-dataset`);
      return handle(res);
    },
    async uploadCSV(file) {
      const fd = new FormData();
      fd.append("file", file);
      const res = await fetch(`${BASE}/upload`, { method: "POST", body: fd });
      return handle(res);
    },
    async analyze(payload) {
      const res = await fetch(`${BASE}/analyze`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      return handle(res);
    },
    async simulate(groupARate, groupBRate) {
      const res = await fetch(`${BASE}/simulate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ group_a_rate: groupARate, group_b_rate: groupBRate }),
      });
      return handle(res);
    },
    reportURL(datasetId) {
      return `${BASE}/report?dataset_id=${encodeURIComponent(datasetId)}`;
    },
  };
})();
