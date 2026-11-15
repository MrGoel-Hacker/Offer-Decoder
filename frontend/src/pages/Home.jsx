import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { http } from "@/lib/api";
import { SmartInput } from "@/components/SmartInput";
import { ManualForm } from "@/components/ManualForm";
import { ReportView } from "@/components/report/ReportView";
import { useAuth } from "@/lib/auth";
import { AuthModal } from "@/components/AuthModal";

const Hero = ({ country }) => (
  <section className="pt-6 sm:pt-9 pb-6">
    <p className="eyebrow fade-up">{country === "us" ? "US offer letters, decoded" : "Indian offer letters, decoded"}</p>
    <h1 className="fade-up mt-3 font-display text-3xl sm:text-5xl font-extrabold leading-[1.08] tracking-tight text-[var(--text)]" style={{ animationDelay: "60ms" }} data-testid="landing-hero-title">
      {country === "us" ? (
        <>Your comp isn't your paycheck.<br /><span className="text-[var(--accent-text)]">See what actually lands.</span></>
      ) : (
        <>Your CTC isn't your salary.<br /><span className="text-[var(--accent-text)]">See what actually lands.</span></>
      )}
    </h1>
    <p className="fade-up mt-4 max-w-xl text-sm sm:text-base text-[var(--text-dim)]" style={{ animationDelay: "100ms" }} data-testid="landing-hero-subtitle">
      {country === "us"
        ? "Upload your offer for take-home pay, taxes, equity, red flags and negotiation tips."
        : "Upload your offer for monthly in-hand salary, a CTC breakdown, red flags and negotiation tips."}
    </p>
    <p className="mt-3 text-sm font-semibold text-[var(--accent-text)]" data-testid="first-report-offer">Your first full report is free. Sign in with Google. No card required.</p>
  </section>
);

const OfferInfo = ({ limits, payments, country }) => <div>
    {payments?.enabled && <div className="mt-5 rounded-xl border border-emerald-500/25 bg-emerald-500/5 p-4 text-sm text-[var(--text-dim)]">
      <p className="font-semibold text-emerald-400">Launch gift · 75% off each full report</p>
      <p className="mt-1">After your free report: {country === "us" ? <><del>US$20</del> <strong className="text-[var(--text)]">US$5</strong></> : <><del>₹500</del> <strong className="text-[var(--text)]">₹125</strong></>} each. One-time payment per offer, no subscription. Taxes, if any, appear at checkout.</p>
      {payments.testMode && <p className="mt-2 text-amber-300">Test payments only — real purchases aren't enabled.</p>}
    </div>}
    {limits && (
      <p className="mt-4 text-xs text-[var(--text-faint)]" data-testid="ai-limits-info">
        {limits.aiConfigured && limits.globalAvailable ? `AI reads left for you today: ${limits.ipRemaining} of 5. Quick scan and manual entry are unlimited.` : `AI reading is paused right now - Quick scan and manual entry work as usual.`}
      </p>
    )}
  </div>;

export default function Home({ country = "in" }) {
  const { user, ready } = useAuth();
  const [showAuth, setShowAuth] = useState(false);
  const pending = useRef(null);
  const authorize = (action) => {
    if (ready && user) return action();
    pending.current = action;
    setShowAuth(true);
  };
  const [manual, setManual] = useState(null); // null | prefill object
  const [session, setSession] = useState(null);
  const [limits, setLimits] = useState(null);
  const [payments, setPayments] = useState(null);

  useEffect(() => {
    http.get(`/payments/config?country=${country}`).then(({ data }) => setPayments(data)).catch(() => {});
  }, [country]);

  useEffect(() => {
    if (!session) http.get("/limits").then((r) => setLimits(r.data)).catch(() => {});
    window.scrollTo({ top: 0, behavior: "smooth" });
  }, [session]);

  const toManual = (p) => setManual(p || {});
  const reset = () => {
    setSession(null);
    setManual(null);
  };

  if (session) return <main className="max-w-3xl mx-auto px-5"><ReportView session={session} onReset={reset} /></main>;

  return (
    <main className="max-w-3xl mx-auto px-5" data-testid="landing-page">
      <Hero country={country} />
      {sessionStorage.getItem("offerdecode:lastReport") && <p className="mb-4 text-sm"><a className="text-[var(--accent-text)] underline" href={`/checkout/${sessionStorage.getItem("offerdecode:lastReport")}`}>Return to your last purchase</a></p>}
      <SmartInput key={country} country={country} onDecoded={setSession} onQuickScan={toManual} authorize={authorize} />
      <OfferInfo limits={limits} payments={payments} country={country} />
      <p className="mt-3 text-center text-[11px] text-[var(--text-faint)] fade-up" style={{ animationDelay: "400ms" }} data-testid="upload-privacy-note">
        Uploads are processed in memory and never stored.{" "}
        <Link to="/privacy" className="text-[var(--text-dim)] underline underline-offset-2 hover:text-[var(--accent-text)]">How your letter is handled</Link>
      </p>
      <div className="mt-6">
        {manual !== null && (
          <ManualForm key={`${country}-${JSON.stringify(manual)}`} country={country} prefill={manual} onSubmit={(data) => authorize(() => setSession(data))} />
        )}
      </div>
      <AuthModal open={showAuth} title="Sign in to decode your offer" subtitle="Continue with Google to decode your offer and keep your purchased reports together. Your selected file stays ready."
        onClose={() => { setShowAuth(false); pending.current = null; }}
        onDone={() => { setShowAuth(false); const action = pending.current; pending.current = null; action?.(); }} />
    </main>
  );
}
