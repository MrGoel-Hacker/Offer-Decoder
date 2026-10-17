import { inr } from "@/lib/format";

export const Headline = ({ r }) => {
  const d = r.derived;
  const nonCash = d.employerPF + d.gratuity + d.otherNonCash;
  const hasVar = d.variable > 0;
  return (
    <section className="card fade-up relative overflow-hidden border-emerald-500/25" data-testid="headline-card">
      <div className="pointer-events-none absolute -right-16 -top-16 h-56 w-56 rounded-full bg-emerald-500/10 blur-3xl" />
      <p className="eyebrow">Fixed in-hand per month</p>
      <p className="mt-3 font-num text-5xl sm:text-6xl font-bold tracking-tight text-emerald-400" data-testid="monthly-fixed-value">
        {inr(r.monthlyFixed)}
      </p>
      <div className="mt-5 flex flex-wrap gap-x-8 gap-y-3">
        {hasVar && (
          <div>
            <p className="text-xs text-slate-500">With variable (if paid 100%)</p>
            <p className="font-num text-xl font-bold text-slate-100" data-testid="monthly-with-variable-value">{inr(r.monthlyWithVariable)}<span className="text-sm text-slate-500">/mo</span></p>
          </div>
        )}
        <div>
          <p className="text-xs text-slate-500">Fixed take-home per year</p>
          <p className="font-num text-xl font-bold text-slate-100" data-testid="annual-takehome-value">{inr(r.annualTakeHomeFixed)}</p>
        </div>
        <div>
          <p className="text-xs text-slate-500">Headline CTC</p>
          <p className="font-num text-xl font-bold text-slate-400" data-testid="ctc-value">{inr(r.ctc)}</p>
        </div>
        {d.joining > 0 && (
          <div>
            <p className="text-xs text-slate-500">Joining bonus after tax (rough, one-time)</p>
            <p className="font-num text-xl font-bold text-slate-100" data-testid="joining-after-tax-value">{inr(r.joiningAfterTax)}</p>
          </div>
        )}
      </div>
      <p className="mt-6 border-t border-[#1c2536] pt-4 text-sm leading-relaxed text-slate-400" data-testid="how-we-got-this">
        <span className="font-semibold text-slate-200">How we got this: </span>
        fixed CTC {inr(r.fixedCTC)} − employer PF, gratuity & non-cash {inr(nonCash)} = cash {inr(r.cashGross)}; minus your PF {inr(d.employeePF)}, professional tax {inr(d.profTax)} and income tax {inr(r.taxFixed.totalTax)} = {inr(r.annualTakeHomeFixed)} ÷ 12.
      </p>
    </section>
  );
};
