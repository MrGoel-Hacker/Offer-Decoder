import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { http } from "@/lib/api";
import { ModeCards } from "@/components/ModeCards";
import { PasteMode } from "@/components/PasteMode";
import { PdfMode } from "@/components/PdfMode";
import { ImageMode } from "@/components/ImageMode";
import { ManualForm } from "@/components/ManualForm";
import { ReportView } from "@/components/report/ReportView";

const Hero = ({ limits }) => (
  <section className="pt-8 sm:pt-14 pb-8">
    <p className="eyebrow fade-up">Indian offer letters, decoded</p>
    <h1 className="fade-up mt-4 font-display text-4xl sm:text-5xl lg:text-6xl font-extrabold leading-[1.02] tracking-tight text-slate-50" style={{ animationDelay: "60ms" }} data-testid="landing-hero-title">
      Your CTC isn't your salary.<br />
      <span className="text-emerald-400">See what actually lands.</span>
    </h1>
    <p className="fade-up mt-5 max-w-xl text-base text-slate-400" style={{ animationDelay: "100ms" }} data-testid="landing-hero-subtitle">
      Drop in your offer and get the real monthly in-hand, a full CTC breakdown, red flags and what to negotiate - with tax math done to the rupee for FY 2026-27.
    </p>
    {limits && (
      <p className="mt-4 text-xs text-slate-500" data-testid="ai-limits-info">
        {limits.aiConfigured && limits.globalAvailable ? `AI reads left for you today: ${limits.ipRemaining} of 5. Quick scan and manual entry are unlimited.` : "AI reading is paused right now - Quick scan and manual entry work as usual."}
      </p>
    )}
  </section>
);

export default function Home() {
  const [mode, setMode] = useState(null);
  const [session, setSession] = useState(null);
  const [prefill, setPrefill] = useState(null);
  const [limits, setLimits] = useState(null);

  useEffect(() => {
    if (!session) http.get("/limits").then((r) => setLimits(r.data)).catch(() => {});
    window.scrollTo({ top: 0, behavior: "smooth" });
  }, [session]);

  const toManual = (p) => {
    setPrefill(p);
    setMode("manual");
  };
  const reset = () => {
    setSession(null);
    setPrefill(null);
    setMode(null);
  };

  if (session) return <main className="max-w-3xl mx-auto px-5"><ReportView session={session} onReset={reset} /></main>;

  const props = { onDecoded: setSession, onQuickScan: toManual };
  return (
    <main className="max-w-3xl mx-auto px-5" data-testid="landing-page">
      <Hero limits={limits} />
      <ModeCards active={mode} onPick={(m) => { setMode(m); if (m === "manual") setPrefill(null); }} />
      <p className="mt-3 text-center text-[11px] text-slate-500 fade-up" style={{ animationDelay: "400ms" }} data-testid="upload-privacy-note">
        Uploads are processed in memory and never stored.{" "}
        <Link to="/privacy" className="text-slate-400 underline underline-offset-2 hover:text-emerald-400">How your letter is handled</Link>
      </p>
      <div className="mt-6">
        {mode === "paste" && <PasteMode {...props} />}
        {mode === "pdf" && <PdfMode {...props} />}
        {mode === "image" && <ImageMode {...props} />}
        {mode === "manual" && <ManualForm key={JSON.stringify(prefill)} prefill={prefill} onSubmit={setSession} />}
      </div>
    </main>
  );
}
