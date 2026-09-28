/* FairLens deployment configuration */
window.FAIRLENS_API_BASE = window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1"
  ? "http://localhost:8000/api"
  : "https://fairlens.onrender.com/api";