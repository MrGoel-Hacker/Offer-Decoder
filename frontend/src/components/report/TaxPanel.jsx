import { inr } from "@/lib/format";

const Row = ({ label, value, strong, minus, testId }) => (
  <div className={`flex items-baseline justify-between gap-4 py-2.5 ${strong ? "border-t border-slate-600 mt-1 pt-3.5" : "border-t border-[#1c2536]"}`}>
    <span className={strong ? "font-semibold text-slate-100" : "text-slate-400"}>{label}</span>
    <span className={`font-num ${strong ? "text-lg font-bold text-emerald-400" : "text-slate-200"}`} data-testid={testId}>
      {minus && value > 0 ? "− " : ""}{inr(value)}
    </span>
  </div>
);

export const TaxPanel = ({ r }) => {
  const t = r.taxFixed;
  return (
    <section className="card fade-up text-sm" data-testid="tax-panel">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <h2 className="font-display text-xl font-bold text-slate-100">Income tax on fixed pay</h2>
        <span className="text-[11px] text-slate-500" data-testid="tax-regime">{r.meta.regime}</span>
      </div>
      <div className="mt-4">
        <Row label="Cash salary (gross)" value={r.cashGross} testId="tax-cash-gross" />
        <Row label="Standard deduction" value={r.standardDeduction} minus testId="tax-standard-deduction" />
        <Row label="Taxable income" value={t.taxable} testId="tax-taxable-income" />
        <Row label="Tax as per slabs" value={t.slabTax} testId="tax-slab-tax" />
        <Row label="Rebate u/s 87A" value={t.rebate} minus testId="tax-rebate" />
        <Row label="Health & education cess (4%)" value={t.cess} testId="tax-cess" />
        <Row label="Total tax per year" value={t.totalTax} strong testId="tax-total" />
      </div>
      {r.derived.variable > 0 && (
        <p className="mt-4 text-xs text-slate-500" data-testid="tax-on-variable">
          Extra tax if the full variable pay is paid: <span className="font-num text-slate-300">{inr(r.taxOnVariable)}</span>
        </p>
      )}
      <p className="mt-2 text-[11px] text-slate-600">Slabs: {r.meta.slabsVerifiedAgainst}.</p>
    </section>
  );
};
