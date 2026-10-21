import axios from "axios";

export const http = axios.create({
  baseURL: `${process.env.REACT_APP_BACKEND_URL ?? ""}/api`,
  timeout: 150000,
});

export const errMsg = (e, fallback = "Something went wrong. Try again.") =>
  e?.response?.data?.detail && typeof e.response.data.detail === "string" ? e.response.data.detail : fallback;

export const toPayload = (input) => {
  const out = {};
  Object.entries(input || {}).forEach(([k, v]) => {
    if (v !== "" && v !== null && v !== undefined) out[k] = v;
  });
  return out;
};
