import { inr } from "@/lib/format";

const ROWS = [
  { k: "basic", label: "Basic", kind: "Monthly cash", sw: "bg-emerald-500" },
  { k: "hra", label: "HRA", kind: "Monthly cash", sw: "bg-emerald-400/80" },
  { k: "specialAndOther", label: "Special / other allowances", kind: "Monthly cash", sw: "bg-emerald-300/60" },
  { k: "employerPF", label: "Employer PF", kind: "Locked in PF", sw: "bg-slate-500" },
  { k: "gratuity", label: "Gratuity", kind: "After 5 years", sw: "bg-slate-600" },
  { k: "otherNonCash", label: "Other non-cash", kind: "Not cash", sw: "bg-slate-700" },
  { k: "variable", label: "Variable pay", kind: "Not guaranteed", sw: "hatch" },
  { k: "joining", label: "Joining bonus", kind: "One-time", sw: "hatch opacity-70" },
  { k: "esops", label: "ESOPs", kind: "Paper value", sw: "border border-emerald-500/60 bg-transparent" },
];

export const Breakdown = ({ r }) => {
  const rows = ROWS.map((x) => ({ ...x, v: r.derived[x.k] || 0 })).filter((x) => x.v > 0);
  const total = rows.reduce((a, b) => a + b.v, 0) || 1;
  const pct = (v) => (r.ctc ? ((v / r.ctc) * 100).toFixed(1) : "0");
  return (
    <section className="card fade-up" data-testid="ctc-breakdown">
      <h2 className="font-display text-xl font-bold text-slate-100">CTC breakdown</h2>
      <p className="mt-1 text-sm text-slate-500">Green is cash you get monthly. Grey is deferred or locked. Striped is at risk.</p>
      <div className="mt-5 flex h-4 w-full gap-[3px] overflow-hidden rounded-full" data-testid="ctc-breakdown-bar">
        {rows.map((x) => (
          <div key={x.k} title={`${x.label}: ${inr(x.v)}`} className={`${x.sw} h-full first:rounded-l-full last:rounded-r-full`} style={{ width: `${(x.v / total) * 100}%`, transition: "width .4s" }} />
        ))}
      </div>
      <div className="mt-6 overflow-x-auto">
        <table className="w-full text-sm" data-testid="ctc-breakdown-table">
          <thead>
            <tr className="text-left text-[11px] uppercase tracking-wider text-slate-500">
              <th className="pb-3 font-semibold">Component</th>
              <th className="pb-3 text-right font-semibold">Per year</th>
              <th className="hidden pb-3 text-right font-semibold sm:table-cell">Per month</th>
              <th className="pb-3 pl-3 text-right font-semibold">% CTC</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((x) => (
              <tr key={x.k} className="border-t border-[#1c2536]" data-testid={`breakdown-row-${x.k}`}>
                <td className="py-3 pr-2">
                  <span className="flex items-center gap-2.5">
                    <span className={`h-2.5 w-2.5 shrink-0 rounded-sm ${x.sw}`} />
                    <span>
                      <span className="block text-slate-200">{x.label}</span>
                      <span className="block text-[11px] text-slate-500">{x.kind}</span>
                    </span>
                  </span>
                </td>
                <td className="py-3 text-right font-num text-slate-100">{inr(x.v)}</td>
                <td className="hidden py-3 text-right font-num text-slate-400 sm:table-cell">{inr(x.v / 12)}</td>
                <td className="py-3 pl-3 text-right font-num text-slate-400">{pct(x.v)}%</td>
              </tr>
            ))}
            <tr className="border-t border-slate-600">
              <td className="py-3 font-semibold text-slate-100">Total CTC</td>
              <td className="py-3 text-right font-num font-bold text-slate-50" data-testid="breakdown-total">{inr(r.ctc)}</td>
              <td className="hidden py-3 text-right font-num text-slate-400 sm:table-cell">{inr(r.ctc / 12)}</td>
              <td className="py-3 text-right font-num text-slate-400">100%</td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>
  );
};
