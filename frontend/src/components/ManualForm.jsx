import { useState } from "react";
import { ArrowRight, FlaskConical } from "lucide-react";
import { toast } from "sonner";
import { FIELDS, fromFields } from "@/lib/fields";
import { AmountInput } from "@/components/AmountInput";
import { lakhs } from "@/lib/format";

export const ManualForm = ({ prefill, onSubmit }) => {
  const [values, setValues] = useState(() => fromFields(prefill?.fields));
  const [notes, setNotes] = useState("");
  const set = (k) => (v) => setValues((s) => ({ ...s, [k]: v }));

  const submit = (e) => {
    e.preventDefault();
    if (!values.ctc) return toast.error("Enter the total CTC to decode.");
    onSubmit({ input: values, notes, clauseFlags: prefill?.clauseFlags || [], source: prefill?.beta ? "quickscan" : "manual" });
  };

  return (
    <form className="card fade-up" onSubmit={submit} data-testid="manual-mode-panel">
      <h2 className="font-display text-lg font-bold text-slate-100">Enter the numbers (annual ₹)</h2>
      {prefill?.beta && (
        <div className="mt-4 rounded-xl border border-amber-500/30 bg-amber-500/[0.07] p-3.5 text-sm text-amber-100" data-testid="quickscan-beta-banner">
          <p className="flex items-center gap-2 font-semibold"><FlaskConical size={15} className="text-amber-400" /> Quick scan · Beta - verify every number</p>
          <p className="mt-1 text-xs text-amber-200/80">Pre-filled from your text by pattern matching, without AI. Found: {Object.keys(prefill.fields || {}).length} values{prefill.clauseFlags?.length ? `, ${prefill.clauseFlags.length} clause flags` : ""}.</p>
          {prefill.scanNotes?.map((n) => <p key={n} className="mt-1 text-xs text-amber-200/70">• {n}</p>)}
        </div>
      )}
      <div className="mt-5 grid grid-cols-1 sm:grid-cols-2 gap-x-4 gap-y-5">
        {FIELDS.map((f) => (
          <div key={f.key} className={f.key === "ctc" ? "sm:col-span-2" : ""}>
            <label htmlFor={`m-${f.key}`} className="flex items-baseline justify-between text-sm font-semibold text-slate-200">
              {f.label}
              {values[f.key] ? <span className="font-num text-xs text-emerald-400/80">{lakhs(values[f.key])}</span> : null}
            </label>
            <div className="mt-1.5">
              <AmountInput id={`m-${f.key}`} value={values[f.key]} onChange={set(f.key)} placeholder={f.key === "ctc" ? "18,00,000" : "Leave blank to assume"} testId={`manual-${f.key}-input`} />
            </div>
            <p className="mt-1 text-[11px] text-slate-500">{f.hint}</p>
          </div>
        ))}
        <div className="sm:col-span-2">
          <label htmlFor="m-notes" className="text-sm font-semibold text-slate-200">Notes (clauses, bond, notice period…)</label>
          <textarea id="m-notes" rows={3} className="field mt-1.5 text-sm" value={notes} onChange={(e) => setNotes(e.target.value)} placeholder="e.g. 2-year service bond of Rs 2 lakh, notice period 90 days" data-testid="manual-notes-textarea" />
          <p className="mt-1 text-[11px] text-slate-500">Scanned offline for risky clauses - no AI.</p>
        </div>
      </div>
      <button type="submit" className="btn-accent mt-6 w-full sm:w-auto" data-testid="manual-decode-button">
        Decode my offer <ArrowRight size={16} />
      </button>
    </form>
  );
};
