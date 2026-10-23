import { AlertTriangle, Info } from "lucide-react";

const FlagItem = ({ f, i }) => {
  const warn = f.level === "warn";
  return (
    <li className="border-t border-[var(--line)] py-5 first:border-t-0 first:pt-0" data-testid={`red-flag-${i}`}>
      <div className="flex gap-3">
        <span className={`mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-lg ${warn ? "bg-amber-500/10 text-[var(--warn-strong)]" : "bg-[var(--chip)] text-[var(--text-dim)]"}`}>
          {warn ? <AlertTriangle size={15} /> : <Info size={15} />}
        </span>
        <div className="flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <span className={`rounded-full px-2 py-0.5 text-[10px] font-bold uppercase tracking-wide ${warn ? "border border-amber-500/30 text-[var(--warn-strong)]" : "border border-[var(--line-3)] text-[var(--text-dim)]"}`}>{warn ? "Watch out" : "Good to know"}</span>
            <span className="text-[10px] uppercase tracking-wide text-[var(--text-xfaint)]">{f.source === "clause" ? "From the letter" : "From the numbers"}</span>
          </div>
          <p className="mt-2 text-[15px] font-semibold leading-snug text-[var(--text)]">{f.text}</p>
          {f.letter && <p className="mt-2 rounded-lg border border-amber-500/20 bg-amber-500/[0.05] px-3 py-2 text-sm text-[var(--warn-text)]" data-testid={`red-flag-letter-${i}`}><span className="font-semibold">In your letter: </span>{f.letter}</p>}
          <p className="mt-2 text-sm text-[var(--text-dim)]"><span className="font-semibold text-[var(--text-2)]">Why it matters: </span>{f.why}</p>
          <p className="mt-1.5 text-sm text-[var(--text-dim)]"><span className="font-semibold text-[var(--accent-text)]">What to ask: </span>“{f.ask}”</p>
        </div>
      </div>
    </li>
  );
};

export const Flags = ({ flags }) => (
  <section className="card fade-up" data-testid="red-flags-card">
    <h2 className="font-display text-xl font-bold text-[var(--text)]">Red flags <span className="font-num text-base text-[var(--text)]0">({flags.length})</span></h2>
    {flags.length ? (
      <ul className="mt-5">{flags.map((f, i) => <FlagItem key={`${f.text}-${i}`} f={f} i={i} />)}</ul>
    ) : (
      <p className="mt-3 text-sm text-[var(--text-dim)]" data-testid="no-flags">Nothing stands out in the numbers. Still read the clauses on bond, notice and non-compete before signing.</p>
    )}
  </section>
);
