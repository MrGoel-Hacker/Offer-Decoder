import { money } from "@/lib/format";

const Stat = ({ label, value, suffix, testId, dim }) => (
  <div>
    <p className="text-xs text-[var(--text-faint)]">{label}</p>
    <p className={`font-num text-xl font-bold ${dim ? "text-[var(--text-dim)]" : "text-[var(--text)]"}`} data-testid={testId}>
      {value}{suffix && <span className="text-sm text-[var(--text-faint)]">{suffix}</span>}
    </p>
  </div>
);

const ScopeNote = ({ children }) => (
  <p className="mt-4 rounded-lg border border-[var(--line)] bg-[var(--field-bg)] px-3 py-2 text-[11px] leading-relaxed text-[var(--text-dim)]" data-testid="scope-note">{children}</p>
);

export const Headline = ({ r }) => {
  const fmt = money(r.country);
  if (r.country === "us") {
    const t = r.taxFixed;
    const hasExtra = r.derived.bonus > 0 || r.derived.rsus > 0;
    return (
      <section className="card fade-up relative overflow-hidden border-emerald-500/25" data-testid="headline-card">
        <div className="pointer-events-none absolute -right-16 -top-16 h-56 w-56 rounded-full bg-emerald-500/10 blur-3xl" />
        <p className="eyebrow">Base salary take-home per month (recurring cash)</p>
        <p className="mt-3 font-num text-5xl sm:text-6xl font-bold tracking-tight text-[var(--accent-text)]" data-testid="monthly-fixed-value">
          {fmt(r.monthlyFixed)}
        </p>
        <ScopeNote>
          Estimate for a <span className="font-semibold">single filer</span> taking the standard deduction{r.stateName ? <> with <span className="font-semibold">{r.stateName}</span> state tax</> : " (no state selected - federal + FICA only)"}. City/local taxes are not included. Bonus, equity and signing bonus are shown separately below - they are not monthly cash.
        </ScopeNote>
        <div className="mt-5 flex flex-wrap gap-x-8 gap-y-3">
          {hasExtra && <Stat label="If bonus + equity pay in full (yearly average, not monthly salary)" value={fmt(r.monthlyWithVariable)} suffix="/mo" testId="monthly-with-variable-value" />}
          <Stat label="Base-salary take-home per year" value={fmt(r.annualTakeHomeFixed)} testId="annual-takehome-value" />
          <Stat label="Total annual comp (base + bonus + equity)" value={fmt(r.ctc)} dim testId="ctc-value" />
          {r.derived.signing > 0 && <Stat label="Signing bonus after tax (rough, one-time)" value={fmt(r.joiningAfterTax)} testId="joining-after-tax-value" />}
        </div>
        <p className="mt-6 border-t border-[var(--line)] pt-4 text-sm leading-relaxed text-[var(--text-dim)]" data-testid="how-we-got-this">
          <span className="font-semibold text-[var(--text-2)]">How we got this: </span>
          gross {fmt(r.cashGross)} − 401(k) {fmt(r.derived.k401)} − federal {fmt(t.federal)} − {r.stateName ? `${r.stateName} ` : ""}state {fmt(t.stateTax)} − Social Security {fmt(t.ss)} − Medicare {fmt(t.medicare)} = {fmt(r.cashGross - r.derived.k401 - t.totalTax)} per year ÷ 12. The 401(k) is still your money, saved pre-tax.
        </p>
      </section>
    );
  }
  const d = r.derived;
  const nonCash = d.employerPF + d.gratuity + d.otherNonCash;
  const hasVar = d.variable > 0;
  return (
    <section className="card fade-up relative overflow-hidden border-emerald-500/25" data-testid="headline-card">
      <div className="pointer-events-none absolute -right-16 -top-16 h-56 w-56 rounded-full bg-emerald-500/10 blur-3xl" />
      <p className="eyebrow">Fixed in-hand per month</p>
      <p className="mt-3 font-num text-5xl sm:text-6xl font-bold tracking-tight text-[var(--accent-text)]" data-testid="monthly-fixed-value">
        {fmt(r.monthlyFixed)}
      </p>
      <div className="mt-5 flex flex-wrap gap-x-8 gap-y-3">
        {hasVar && <Stat label="With variable (if paid 100%)" value={fmt(r.monthlyWithVariable)} suffix="/mo" testId="monthly-with-variable-value" />}
        <Stat label="Fixed take-home per year" value={fmt(r.annualTakeHomeFixed)} testId="annual-takehome-value" />
        <Stat label="Headline CTC" value={fmt(r.ctc)} dim testId="ctc-value" />
        {d.joining > 0 && <Stat label="Joining bonus after tax (rough, one-time)" value={fmt(r.joiningAfterTax)} testId="joining-after-tax-value" />}
      </div>
      <p className="mt-6 border-t border-[var(--line)] pt-4 text-sm leading-relaxed text-[var(--text-dim)]" data-testid="how-we-got-this">
        <span className="font-semibold text-[var(--text-2)]">How we got this: </span>
        fixed CTC {fmt(r.fixedCTC)} − employer PF, gratuity & non-cash {fmt(nonCash)} = cash {fmt(r.cashGross)}; minus your PF {fmt(d.employeePF)}, professional tax {fmt(d.profTax)} and income tax {fmt(r.taxFixed.totalTax)} = {fmt(r.annualTakeHomeFixed)} ÷ 12.
      </p>
    </section>
  );
};
