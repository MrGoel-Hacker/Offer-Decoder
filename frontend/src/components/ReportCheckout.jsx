import { useState } from "react";
import { http, errMsg, toPayload } from "@/lib/api";

export function ReportCheckout({ session, onReset, config }) {
  const [country, setCountry] = useState(session.country === "us" ? "US" : "IN");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [recovery] = useState(() => sessionStorage.getItem("offerdecode:lastReport"));
  const price = config.prices[country];
  const money = (amount) => new Intl.NumberFormat(country === "IN" ? "en-IN" : "en-US", { style: "currency", currency: price.currency, maximumFractionDigits: 0 }).format(amount / 100);

  async function checkout() {
    setBusy(true);
    setError("");
    try {
      const { data } = await http.post("/payments/checkout", {
        ...session, input: toPayload(session.input), country: session.country || "in", billingCountry: country,
      });
      sessionStorage.setItem("offerdecode:lastReport", data.reportToken);
      sessionStorage.setItem(`offerdecode:checkout:${data.reportToken}`, data.checkoutUrl);
      window.location.assign(data.checkoutUrl);
    } catch (e) {
      setError(errMsg(e, "Couldn't start checkout. Please try again."));
      setBusy(false);
    }
  }

  return <section className="py-10 space-y-6" data-testid="report-checkout">
    <p className="eyebrow">Your offer is ready to decode</p>
    <h1 className="font-display text-3xl font-extrabold text-slate-50">One payment. One full report.</h1>
    <p className="text-slate-400">Unlock your in-hand salary, CTC breakdown, tax estimates, red flags and negotiation tips for this offer. No subscription.</p>
    <p className="text-sm text-[var(--text-dim)]">This report uses {session.country === "us" ? "US salary and tax estimates" : "Indian salary and tax rules"}. Billing country only selects your payment price.</p>
    {config.testMode && <p className="text-amber-300">Test checkout — no real payment. Use test payment details only.</p>}
    <label className="block text-sm text-slate-300">Billing country
      <select className="mt-2 block rounded-lg border border-slate-700 bg-slate-900 p-3" value={country} disabled={busy} onChange={(e) => setCountry(e.target.value)}>
        <option value="IN">India — INR</option><option value="US">United States — USD</option>
      </select>
    </label>
    <div><p className="text-emerald-400 text-sm">Launch gift · 75% off</p>
      <p className="mt-2 text-4xl font-bold text-slate-50">{money(price.amount)} <del className="text-lg font-normal text-slate-500">{money(price.original)}</del></p>
      <p className="mt-2 text-xs text-slate-400">Per report. Any applicable taxes are shown at checkout. Your billing country must match your selection.</p>
    </div>
    <p className="text-sm text-slate-400">Your offer details are saved for up to 90 days to deliver your report. Keep the private report link safe; anyone with it can view the report.</p>
    {error && <p role="alert" className="text-red-400">{error}</p>}
    <div className="flex flex-wrap gap-3">
      <button className="btn-primary" disabled={busy} onClick={checkout}>{busy ? "Opening secure checkout…" : `Unlock report · ${money(price.amount)}`}</button>
      <button className="btn-ghost" disabled={busy} onClick={onReset}>Edit offer</button>
    </div>
    {recovery && <a className="block text-sm text-emerald-400" href={`/checkout/${recovery}`}>Return to your last purchase</a>}
  </section>;
}
