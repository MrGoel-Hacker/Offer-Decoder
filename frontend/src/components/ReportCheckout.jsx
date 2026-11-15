import { useState } from "react";
import { http, errMsg, toPayload } from "@/lib/api";
import { CreditCard, ArrowRight, CheckCircle2 } from "lucide-react";
import { useAuth } from "@/lib/auth";
import { AuthModal } from "@/components/AuthModal";

export function ReportCheckout({ session, onReset, config }) {
  const { user, authHeaders } = useAuth();
  const [showAuth, setShowAuth] = useState(false);
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
      }, { headers: authHeaders() });
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
    <h1 className="font-display text-3xl font-extrabold text-[var(--text)]">Unlock your full offer report</h1>
    <p className="text-[var(--text-dim)]">Unlock your in-hand salary, CTC breakdown, tax estimates, red flags and negotiation tips for this offer. No subscription.</p>
    <p className="text-sm text-[var(--text-dim)]">This report uses {session.country === "us" ? "US salary and tax estimates" : "Indian salary and tax rules"}. Billing country only selects your payment price.</p>
    {config.testMode && <p className="text-amber-300">Test checkout — no real payment. Use test payment details only.</p>}
    <label className="block text-sm text-[var(--text-dim)]">Billing country
      <select className="mt-2 block rounded-lg border border-[var(--line-2)] bg-[var(--field-bg)] p-3" value={country} disabled={busy} onChange={(e) => setCountry(e.target.value)}>
        <option value="IN">India — INR</option><option value="US">United States — USD</option>
      </select>
    </label>
    <div className="rounded-2xl border-2 border-emerald-500/50 bg-emerald-500/[0.07] p-6 sm:p-8"><p className="text-[var(--accent-text)] text-sm font-semibold">Launch gift · 75% off</p>
      <p className="mt-2 text-4xl font-bold text-[var(--text)]">{money(price.amount)} <del className="text-lg font-normal text-[var(--text-dim)]">{money(price.original)}</del></p>
      <ul className="my-5 space-y-2 text-sm text-[var(--text)]">
        {["Full salary breakdown, tax estimates and offer flags", "Downloadable PDF report to keep", "Saved in My Reports, with an optional share link"].map((item) => <li key={item} className="flex items-start gap-2"><CheckCircle2 size={17} className="mt-0.5 shrink-0 text-[var(--accent-text)]" />{item}</li>)}
      </ul>
      <button className="btn-accent w-full !py-4 !text-base" disabled={busy} onClick={() => user ? checkout() : setShowAuth(true)} data-testid="pay-unlock-button"><CreditCard size={20} />{busy ? "Opening secure checkout…" : `Pay ${money(price.amount)} & unlock report`}<ArrowRight size={19} /></button>
      <p className="mt-3 text-center text-xs text-[var(--text-dim)]">Secure checkout by Dodo Payments · One-time payment · No subscription</p>
      <p className="mt-2 text-xs text-[var(--text-dim)]">Per report. Any applicable taxes are shown at checkout. Your billing country must match your selection.</p>
    </div>
    <p className="text-sm text-[var(--text-dim)]">Your offer details are saved for up to 90 days to deliver your report. Keep the private report link safe; anyone with it can view the report.</p>
    {error && <p role="alert" className="text-red-400">{error}</p>}
    <div className="flex flex-wrap gap-3">
      <button className="btn-ghost" disabled={busy} onClick={onReset}>Edit offer</button>
    </div>
    {recovery && <a className="block text-sm text-[var(--accent-text)]" href={`/checkout/${recovery}`}>Return to your last purchase</a>}
    <AuthModal open={showAuth} onClose={() => setShowAuth(false)} onDone={() => { setShowAuth(false); checkout(); }} title="Sign in to save your purchase" subtitle="Use Google to keep this report and its PDF in your account." />
  </section>;
}
