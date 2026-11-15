import { Link } from "react-router-dom";
import { ArrowRight, Globe2 } from "lucide-react";

export default function SelectRegion() {
  return <main className="mx-auto max-w-3xl px-5 py-10 sm:py-16" data-testid="region-selection">
    <Globe2 size={30} className="text-[var(--accent-text)]" />
    <p className="eyebrow mt-5">Your first full report is free</p>
    <h1 className="mt-3 font-display text-4xl font-extrabold tracking-tight text-[var(--text)] sm:text-5xl">Select your region</h1>
    <p className="mt-4 max-w-xl text-[var(--text-dim)]">Get the salary breakdown and tax estimates for your offer. Choose the region that matches your offer and billing country.</p>
    <div className="mt-8 grid gap-4 sm:grid-cols-2">
      <Link to="/india" className="card group block !p-7 hover:!border-emerald-500/70" data-testid="select-india">
        <span className="text-xs font-semibold tracking-widest text-[var(--accent-text)]">INDIA</span>
        <h2 className="mt-3 font-display text-2xl font-bold text-[var(--text)]">Decode an Indian offer</h2>
        <p className="mt-3 text-sm leading-relaxed text-[var(--text-dim)]">Understand your CTC, monthly in-hand, PF, gratuity and offer clauses.</p>
        <span className="mt-6 flex items-center gap-2 font-semibold text-[var(--accent-text)]">Continue to India <ArrowRight size={18} /></span>
      </Link>
      <Link to="/usa" className="card group block !p-7 hover:!border-emerald-500/70" data-testid="select-usa">
        <span className="text-xs font-semibold tracking-widest text-[var(--accent-text)]">UNITED STATES</span>
        <h2 className="mt-3 font-display text-2xl font-bold text-[var(--text)]">Decode a US offer</h2>
        <p className="mt-3 text-sm leading-relaxed text-[var(--text-dim)]">Understand your take-home pay, base salary, bonus, RSUs and offer clauses.</p>
        <span className="mt-6 flex items-center gap-2 font-semibold text-[var(--accent-text)]">Continue to USA <ArrowRight size={18} /></span>
      </Link>
    </div>
    <p className="mt-6 text-xs text-[var(--text-faint)]">Sign in with Google. One free full report per account across both regions, including PDF download. No card required. Later reports are paid.</p>
  </main>;
}
