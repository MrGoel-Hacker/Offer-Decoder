import { AlertTriangle, Info } from "lucide-react";

const FlagItem = ({ f, i }) => {
  const warn = f.level === "warn";
  return (
    <li className="border-t border-[#1c2536] py-5 first:border-t-0 first:pt-0" data-testid={`red-flag-${i}`}>
      <div className="flex gap-3">
        <span className={`mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-lg ${warn ? "bg-amber-500/10 text-amber-400" : "bg-slate-700/40 text-slate-400"}`}>
          {warn ? <AlertTriangle size={15} /> : <Info size={15} />}
        </span>
        <div className="flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <span className={`rounded-full px-2 py-0.5 text-[10px] font-bold uppercase tracking-wide ${warn ? "border border-amber-500/30 text-amber-400" : "border border-slate-600 text-slate-400"}`}>{warn ? "Watch out" : "Good to know"}</span>
            <span className="text-[10px] uppercase tracking-wide text-slate-600">{f.source === "clause" ? "From the letter" : "From the numbers"}</span>
          </div>
          <p className="mt-2 text-[15px] font-semibold leading-snug text-slate-100">{f.text}</p>
          {f.letter && <p className="mt-2 rounded-lg border border-amber-500/20 bg-amber-500/[0.05] px-3 py-2 text-sm text-amber-100" data-testid={`red-flag-letter-${i}`}><span className="font-semibold">In your letter: </span>{f.letter}</p>}
          <p className="mt-2 text-sm text-slate-400"><span className="font-semibold text-slate-300">Why it matters: </span>{f.why}</p>
          <p className="mt-1.5 text-sm text-slate-400"><span className="font-semibold text-emerald-400">What to ask: </span>“{f.ask}”</p>
        </div>
      </div>
    </li>
  );
};

export const Flags = ({ flags }) => (
  <section className="card fade-up" data-testid="red-flags-card">
    <h2 className="font-display text-xl font-bold text-slate-100">Red flags <span className="font-num text-base text-slate-500">({flags.length})</span></h2>
    {flags.length ? (
      <ul className="mt-5">{flags.map((f, i) => <FlagItem key={`${f.text}-${i}`} f={f} i={i} />)}</ul>
    ) : (
      <p className="mt-3 text-sm text-slate-400" data-testid="no-flags">Nothing stands out in the numbers. Still read the clauses on bond, notice and non-compete before signing.</p>
    )}
  </section>
);
