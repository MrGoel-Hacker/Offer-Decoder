import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { http, errMsg } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { AuthModal } from "@/components/AuthModal";

export default function Billing() {
  const { user, ready, authHeaders } = useAuth();
  const [params] = useSearchParams();
  const returned = params.get("returned") === "1";
  const cancelled = params.get("cancelled") === "1";
  const [region, setRegion] = useState(params.get("region") === "us" ? "us" : "in");
  const [packs, setPacks] = useState([]);
  const [status, setStatus] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [showAuth, setShowAuth] = useState(false);
  const [check, setCheck] = useState(0);
  const [checking, setChecking] = useState(returned);

  useEffect(() => {
    http.get("/billing/packs").then(({ data }) => setPacks(data.packs))
      .catch((e) => setError(errMsg(e, "Could not load pricing. Please reload.")));
  }, []);

  useEffect(() => {
    if (!ready || !user) { setStatus(null); return; }
    let active = true;
    let timer;
    let attempts = 0;
    setChecking(returned);
    const load = async () => {
      try {
        const { data } = await http.get("/billing/status", { headers: authHeaders() });
        if (!active) return;
        setStatus(data);
        if (returned && !data.purchased && attempts++ < 15) {
          timer = setTimeout(load, 2000);
        } else {
          setChecking(false);
        }
      } catch (e) {
        if (active) { setError(errMsg(e)); setChecking(false); }
      }
    };
    load();
    return () => { active = false; clearTimeout(timer); };
  }, [user, ready, returned, check, authHeaders]);

  const buy = async () => {
    if (!user) { setShowAuth(true); return; }
    setBusy(true);
    setError("");
    try {
      const { data } = await http.post("/billing/checkout", { region }, { headers: authHeaders() });
      window.location.assign(data.checkoutUrl);
    } catch (e) {
      setError(errMsg(e, "Checkout is unavailable. Please try again."));
      setBusy(false);
    }
  };
  const pack = packs.find((p) => p.region === region);
  const money = (amount) => new Intl.NumberFormat(region === "in" ? "en-IN" : "en-US", {
    style: "currency", currency: pack?.currency || (region === "in" ? "INR" : "USD"),
    maximumFractionDigits: 0,
  }).format(amount / 100);

  return (
    <main className="max-w-3xl mx-auto px-5 py-10">
      <p className="eyebrow">Your first three reports</p>
      <h1 className="font-display mt-3 text-3xl font-extrabold text-[var(--text)]">One pack. Three saved reports.</h1>
      <p className="mt-3 text-sm text-[var(--text-dim)]">Get 75% off your first pack. One payment, no subscription. Preview an offer for free; use one credit when you save a new report.</p>
      {cancelled && <p role="status" className="mt-5 text-sm text-[var(--text-dim)]">Checkout cancelled. You can return whenever you are ready.</p>}
      {error && <p role="alert" className="mt-5 text-sm text-red-500">{error}</p>}
      {user && status && (
        <div className="card mt-6" role="status">
          <p className="font-semibold text-[var(--text)]">{status.credits} report {status.credits === 1 ? "credit" : "credits"} remaining</p>
          {status.refunded ? <p className="mt-2 text-sm text-[var(--text-dim)]">Your payment was refunded. Unused credits have been removed.</p>
            : status.purchased ? <p className="mt-2 text-sm text-[var(--text-dim)]">{status.credits ? "Your pack is ready. Return to your open report tab to save it, or decode another offer." : "You have used your introductory pack. Your saved reports remain available until they expire."}</p>
            : returned ? <p className="mt-2 text-sm text-[var(--text-dim)]">{checking ? "Waiting for payment confirmation…" : "Payment has not been confirmed yet. If you paid, check again shortly before trying another payment."}</p> : null}
          <button type="button" className="mt-3 text-sm underline text-[var(--accent-text)]" onClick={() => setCheck((v) => v + 1)}>Check payment status</button>
        </div>
      )}
      {!status?.purchased && (
        <section className="card mt-6">
          <label htmlFor="billing-region" className="block text-sm font-semibold text-[var(--text)]">Billing country</label>
          <select id="billing-region" value={region} onChange={(e) => setRegion(e.target.value)} className="field mt-2" disabled={busy}>
            <option value="in">India · INR</option><option value="us">United States · USD</option>
          </select>
          {pack && <>
            <p className="mt-5 text-sm text-[var(--text-dim)]"><s>{money(pack.originalAmount)}</s> <span className="ml-2 font-semibold text-[var(--accent-text)]">75% off</span></p>
            <p className="mt-1 text-4xl font-bold text-[var(--text)]">{money(pack.amount)} <span className="text-sm font-normal text-[var(--text-dim)]">total for 3 reports</span></p>
            <p className="mt-3 text-xs text-[var(--text-dim)]">Includes applicable taxes. Select your billing country; it is independent of the country of your job offer. Offer available once per account.</p>
          </>}
          <button type="button" onClick={buy} disabled={busy || !ready || !pack?.available || (!!user && !status) || checking} className="btn-accent mt-5">
            {busy ? "Opening checkout…" : !pack ? "Loading…" : !pack.available ? "Payments coming soon" : "Get 3 report credits"}
          </button>
        </section>
      )}
      <p className="mt-5 text-xs text-[var(--text-dim)]">Saved reports expire after 90 days. Reopening and sharing a saved report use no additional credits. Deleting a report does not restore its credit. Existing reports remain accessible.</p>
      <div className="mt-6 flex gap-5 text-sm text-[var(--accent-text)]"><Link to="/">Decode an offer</Link><Link to="/my/reports">My reports</Link></div>
      <AuthModal open={showAuth && !user} onClose={() => setShowAuth(false)} title="Sign in to buy your report pack" subtitle="Your three report credits will belong to this Google account. After signing in, choose Get 3 report credits to continue." />
    </main>
  );
}
