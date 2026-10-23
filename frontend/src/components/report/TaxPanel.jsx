import { money } from "@/lib/format";

const Row = ({ label, value, strong, minus, testId, fmt }) => (
  <div className={`flex items-baseline justify-between gap-4 py-2.5 ${strong ? "border-t border-[var(--line-3)] mt-1 pt-3.5" : "border-t border-[var(--line)]"}`}>
    <span className={strong ? "font-semibold text-[var(--text)]" : "text-[var(--text-dim)]"}>{label}</span>
    <span className={`font-num ${strong ? "text-lg font-bold text-[var(--accent-text)]" : "text-[var(--text-2)]"}`} data-testid={testId}>
      {minus && value > 0 ? "− " : ""}{fmt(value)}
    </span>
  </div>
);

export const TaxPanel = ({ r }) => {
  const fmt = money(r.country);
  const t = r.taxFixed;
  if (r.country === "us") {
    return (
      <section className="card fade-up text-sm" data-testid="tax-panel">
        <div className="flex flex-wrap items-baseline justify-between gap-2">
          <h2 className="font-display text-xl font-bold text-[var(--text)]">Taxes on this offer</h2>
          <span className="text-[11px] text-[var(--text-faint)]" data-testid="tax-regime">{r.meta.regime}</span>
        </div>
        <div className="mt-4">
          <Row fmt={fmt} label="Gross pay (base + bonus + equity)" value={r.cashGross} testId="tax-cash-gross" />
          <Row fmt={fmt} label="Your 401(k) contribution" value={r.derived.k401} minus testId="tax-k401" />
          <Row fmt={fmt} label="Federal standard deduction" value={r.standardDeduction} minus testId="tax-standard-deduction" />
          <Row fmt={fmt} label="Federal taxable income" value={t.taxable} testId="tax-taxable-income" />
          <Row fmt={fmt} label="Federal income tax" value={t.federal} testId="tax-federal" />
          <Row fmt={fmt} label={r.stateName ? `State tax (${r.stateName})` : "State tax"} value={t.stateTax} testId="tax-state" />
          <Row fmt={fmt} label="Social Security (6.2% up to $184,500)" value={t.ss} testId="tax-ss" />
          <Row fmt={fmt} label="Medicare (1.45%, +0.9% over $200k)" value={t.medicare} testId="tax-medicare" />
          <Row fmt={fmt} label="Total taxes per year" value={t.totalTax} strong testId="tax-total" />
        </div>
        {r.derived.bonus > 0 && (
          <p className="mt-4 text-xs text-[var(--text-faint)]" data-testid="tax-on-variable">
            Extra tax if the full bonus is paid: <span className="font-num text-[var(--text-2)]">{fmt(r.taxOnVariable)}</span>
          </p>
        )}
        <p className="mt-3 rounded-lg border border-[var(--line)] bg-[var(--field-bg)] px-3 py-2 text-[11px] leading-relaxed text-[var(--text-dim)]" data-testid="tax-scope-note">
          {r.meta.countryNote} State figures use Tax Foundation's 2026 tables - a good estimate, not verified against each state's own revenue department. Numbers: {r.meta.slabsVerifiedAgainst}.
        </p>
      </section>
    );
  }
  return (
    <section className="card fade-up text-sm" data-testid="tax-panel">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <h2 className="font-display text-xl font-bold text-[var(--text)]">Income tax on fixed pay</h2>
        <span className="text-[11px] text-[var(--text-faint)]" data-testid="tax-regime">{r.meta.regime}</span>
      </div>
      <div className="mt-4">
        <Row fmt={fmt} label="Cash salary (gross)" value={r.cashGross} testId="tax-cash-gross" />
        <Row fmt={fmt} label="Standard deduction" value={r.standardDeduction} minus testId="tax-standard-deduction" />
        <Row fmt={fmt} label="Taxable income" value={t.taxable} testId="tax-taxable-income" />
        <Row fmt={fmt} label="Tax as per slabs" value={t.slabTax} testId="tax-slab-tax" />
        <Row fmt={fmt} label="Rebate u/s 87A" value={t.rebate} minus testId="tax-rebate" />
        <Row fmt={fmt} label="Health & education cess (4%)" value={t.cess} testId="tax-cess" />
        <Row fmt={fmt} label="Total tax per year" value={t.totalTax} strong testId="tax-total" />
      </div>
      {r.derived.variable > 0 && (
        <p className="mt-4 text-xs text-[var(--text-faint)]" data-testid="tax-on-variable">
          Extra tax if the full variable pay is paid: <span className="font-num text-[var(--text-2)]">{fmt(r.taxOnVariable)}</span>
        </p>
      )}
      <p className="mt-2 text-[11px] text-[var(--text-xfaint)]">Slabs: {r.meta.slabsVerifiedAgainst}.</p>
    </section>
  );
};
