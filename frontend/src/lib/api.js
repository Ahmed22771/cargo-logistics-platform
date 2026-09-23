import axios from "axios";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
export const API = `${BACKEND_URL}/api`;

const api = axios.create({ baseURL: API });

api.interceptors.request.use((config) => {
  const token = localStorage.getItem("cargo_token");
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

export function apiErr(e, fallback = "Something went wrong") {
  const d = e?.response?.data?.detail;
  if (typeof d === "string") return d;
  if (Array.isArray(d)) return d.map((x) => x?.msg || "").join(" ");
  // Structured error objects (e.g. eligibility gate): { code, reasons: [...] }
  if (d && typeof d === "object") {
    if (Array.isArray(d.reasons) && d.reasons.length) {
      return d.reasons.map((r) => r?.message || r?.code || "").filter(Boolean).join(" • ");
    }
    if (d.code) return d.code;
  }
  return fallback;
}

// Extract a structured eligibility rejection (403 { code:"NOT_ELIGIBLE", reasons:[...] }).
// Returns { code, reasons } or null so callers can localize the message.
export function eligibilityError(e) {
  const d = e?.response?.data?.detail;
  if (e?.response?.status === 403 && d && typeof d === "object" && !Array.isArray(d) && d.code === "NOT_ELIGIBLE") {
    return { code: d.code, reasons: Array.isArray(d.reasons) ? d.reasons : [] };
  }
  return null;
}

export default api;
