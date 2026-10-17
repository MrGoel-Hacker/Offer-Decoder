// Display-only formatting (Indian grouping). All figures come from the backend math.
export function inr(n) {
  if (n === null || n === undefined || !isFinite(n)) return "-";
  const neg = n < 0;
  n = Math.abs(Math.round(n));
  const s = String(n);
  let out = s.length > 3 ? s.slice(-3) : s;
  let rest = s.slice(0, -3);
  while (rest.length > 2) {
    out = rest.slice(-2) + "," + out;
    rest = rest.slice(0, -2);
  }
  if (rest) out = rest + "," + out;
  return (neg ? "-" : "") + "\u20B9" + out;
}

export const group = (v) => (v === "" || v === null || v === undefined ? "" : inr(v).replace("\u20B9", ""));

export const toNum = (s) => {
  const d = String(s ?? "").replace(/[^\d]/g, "");
  return d ? Number(d) : "";
};

export const lakhs = (n) => {
  if (!n) return "";
  if (n >= 1e7) return `${(n / 1e7).toFixed(2).replace(/\.?0+$/, "")} Cr`;
  return `${(n / 1e5).toFixed(2).replace(/\.?0+$/, "")} L`;
};
