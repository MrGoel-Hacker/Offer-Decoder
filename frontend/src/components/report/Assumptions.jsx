import { useState } from "react";
import { ChevronDown } from "lucide-react";
import { Switch } from "@/components/ui/switch";
import { AmountInput } from "@/components/AmountInput";
import { FIELDS } from "@/lib/fields";
import { inr } from "@/lib/format";

const ROWS = [
  { key: "basic", label: "Basic salary", match: /^Basic/, std: "From your input" },
  { key: "employerPF", label: "Employer PF", match: /^Employer PF/, std: "From your input" },
  { key: "gratuity", label: "Gratuity", match: /^Gratuity/, std: "From your input" },
  { key: "employeePF", dKey: "employeePF", label: "Your PF deduction", std: "12% of basic unless you change it" },
  { key: "profTax", dKey: "profTax", label: "Professional tax", std: "Typical state amount ₹2,400/yr unless you change it" },
];

const AssumptionRow = ({ row, r, input, onChange, readOnly }) => {
  const assumed = row.match && r.assumptions.find((a) => row.match.test(a));
  return (
    <div className="grid grid-cols-1 sm:grid-cols-[1fr_200px] items-center gap-3 border-t border-[#1c2536] py-4" data-testid={`assumption-row-${row.key}`}>
      <div>
        <p className="flex items-center gap-2 text-sm font-semibold text-slate-200">
          {row.label}
          {assumed && <span className="rounded-full border border-amber-500/30 bg-amber-500/10 px-2 py-0.5 text-[10px] font-bold uppercase tracking-wide text-amber-400">Assumed</span>}
        </p>
        <p className="mt-0.5 text-xs text-slate-500">{assumed || row.std}</p>
      </div>
      {readOnly ? (
        <p className="font-num text-right text-slate-100">{inr(r.derived[row.dKey || row.key])}</p>
      ) : (
        <AmountInput value={input[row.key] ?? ""} onChange={(v) => onChange(row.key, v)} placeholder={String(inr(r.derived[row.dKey || row.key])).replace("₹", "")} testId={`assumption-${row.key}-input`} />
      )}
    </div>
  );
};

const AllInputs = ({ input, onChange }) => {
  const [open, setOpen] = useState(false);
  return (
    <div className="mt-4">
      <button type="button" onClick={() => setOpen(!open)} className="flex items-center gap-2 text-sm font-semibold text-emerald-400" data-testid="toggle-all-inputs">
        <ChevronDown size={16} style={{ transform: open ? "rotate(180deg)" : "none", transition: "transform .2s" }} /> Edit all offer numbers
      </button>
      {open && (
        <div className="mt-4 grid grid-cols-1 sm:grid-cols-2 gap-4" data-testid="all-inputs-editor">
          {FIELDS.filter((f) => !["basic", "employerPF", "gratuity"].includes(f.key)).map((f) => (
            <div key={f.key}>
              <p className="mb-1.5 text-xs font-semibold text-slate-300">{f.label}</p>
              <AmountInput value={input[f.key] ?? ""} onChange={(v) => onChange(f.key, v)} placeholder="0" testId={`edit-${f.key}-input`} />
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export const Assumptions = ({ r, input, onChange, readOnly }) => (
  <section className="card fade-up" data-testid="assumptions-panel">
    <h2 className="font-display text-xl font-bold text-slate-100">Assumptions</h2>
    <p className="mt-1 text-sm text-slate-500">{readOnly ? "Values used in this report." : "Change any value - the report recalculates instantly. Clear a box to go back to the assumption."}</p>
    <div className="mt-4">
      {ROWS.map((row) => <AssumptionRow key={row.key} row={row} r={r} input={input} onChange={onChange} readOnly={readOnly} />)}
      {!readOnly && (
        <label className="flex items-center justify-between gap-4 border-t border-[#1c2536] pt-4 text-sm text-slate-300">
          Gratuity is part of my CTC
          <Switch checked={input.gratuityInCTC !== false} onCheckedChange={(c) => onChange("gratuityInCTC", c ? "" : false)} data-testid="gratuity-in-ctc-switch" />
        </label>
      )}
    </div>
    {!readOnly && <AllInputs input={input} onChange={onChange} />}
  </section>
);
