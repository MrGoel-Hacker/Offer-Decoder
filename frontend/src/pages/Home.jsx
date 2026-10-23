import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { http } from "@/lib/api";
import { SmartInput } from "@/components/SmartInput";
import { ManualForm } from "@/components/ManualForm";
import { ReportView } from "@/components/report/ReportView";

const CountryToggle = ({ country, onPick }) => (
  <div className="mb-5 inline-flex rounded-full border border-[var(--line-2)] bg-[var(--field-bg)] p-1" data-testid="country-toggle" style={{ animationDelay: "80ms" }}>
    {[
      { id: "in", label: "India ₹" },
      { id: "us", label: "USA $" },
    ].map((c) => (
      <button
        key={c.id}
        type="button"
        onClick={() => onPick(c.id)}
        className={`rounded-full px-5 py-2 text-sm font-bold ${country === c.id ? "bg-emerald-500 text-[#04130d]" : "text-[var(--text-dim)] hover:text-[var(--text)]"}`}
        style={{ transition: "background-color .2s, color .2s" }}
        data-testid={`country-${c.id}-button`}
      >
        {c.label}
      </button>
    ))}
  </div>
);

const Hero = ({ limits, country }) => (
  <section className="pt-8 sm:pt-14 pb-8">
    <p className="eyebrow fade-up">{country === "us" ? "US offer letters, decoded" : "Indian offer letters, decoded"}</p>
    <h1 className="fade-up mt-4 font-display text-4xl sm:text-5xl lg:text-6xl font-extrabold leading-[1.02] tracking-tight text-[var(--text)]" style={{ animationDelay: "60ms" }} data-testid="landing-hero-title">
      {country === "us" ? (
        <>Your comp isn't your paycheck.<br /><span className="text-[var(--accent-text)]">See what actually lands.</span></>
      ) : (
        <>Your CTC isn't your salary.<br /><span className="text-[var(--accent-text)]">See what actually lands.</span></>
      )}
    </h1>
    <p className="fade-up mt-5 max-w-xl text-base text-[var(--text-dim)]" style={{ animationDelay: "100ms" }} data-testid="landing-hero-subtitle">
      {country === "us"
        ? "Drop in your offer and get the real monthly take-home, a full comp breakdown, red flags and what to negotiate - with 2026 federal, state and FICA math done to the dollar."
        : "Drop in your offer and get the real monthly in-hand, a full CTC breakdown, red flags and what to negotiate - with tax math done to the rupee for FY 2026-27."}
    </p>
    {limits && (
      <p className="mt-4 text-xs text-[var(--text-faint)]" data-testid="ai-limits-info">
        {limits.aiConfigured && limits.globalAvailable ? `AI reads left for you today: ${limits.ipRemaining} of 5. ${country === "us" ? "Manual entry is" : "Quick scan and manual entry are"} unlimited.` : `AI reading is paused right now - ${country === "us" ? "Manual entry works" : "Quick scan and manual entry work"} as usual.`}
      </p>
    )}
  </section>
);

export default function Home() {
  const [country, setCountry] = useState("in");
  const [manual, setManual] = useState(null); // null | prefill object
  const [session, setSession] = useState(null);
  const [limits, setLimits] = useState(null);

  useEffect(() => {
    if (!session) http.get("/limits").then((r) => setLimits(r.data)).catch(() => {});
    window.scrollTo({ top: 0, behavior: "smooth" });
  }, [session]);

  const pickCountry = (c) => {
    setCountry(c);
    setManual(null);
  };

  const toManual = (p) => setManual(p || {});
  const reset = () => {
    setSession(null);
    setManual(null);
  };

  if (session) return <main className="max-w-3xl mx-auto px-5"><ReportView session={session} onReset={reset} /></main>;

  return (
    <main className="max-w-3xl mx-auto px-5" data-testid="landing-page">
      <Hero limits={limits} country={country} />
      <CountryToggle country={country} onPick={pickCountry} />
      <SmartInput key={country} country={country} onDecoded={setSession} onQuickScan={toManual} />
      <p className="mt-3 text-center text-[11px] text-[var(--text-faint)] fade-up" style={{ animationDelay: "400ms" }} data-testid="upload-privacy-note">
        Uploads are processed in memory and never stored.{" "}
        <Link to="/privacy" className="text-[var(--text-dim)] underline underline-offset-2 hover:text-[var(--accent-text)]">How your letter is handled</Link>
      </p>
      <div className="mt-6">
        {manual !== null && (
          <ManualForm key={`${country}-${JSON.stringify(manual)}`} country={country} prefill={manual} onSubmit={setSession} />
        )}
      </div>
    </main>
  );
}
