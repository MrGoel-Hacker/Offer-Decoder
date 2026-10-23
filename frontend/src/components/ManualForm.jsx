import { useState } from "react";
import { ArrowRight, FlaskConical } from "lucide-react";
import { toast } from "sonner";
import { fieldsFor, fromFields } from "@/lib/fields";
import { AmountInput } from "@/components/AmountInput";
import { US_STATES } from "@/lib/states";
import { lakhs, kfmt } from "@/lib/format";

export const ManualForm = ({ prefill, onSubmit, country = "in" }) => {
  const FIELDS = fieldsFor(country);
  const [values, setValues] = useState(() => fromFields(FIELDS, prefill?.fields));
  const [state, setState] = useState(prefill?.state || "");
  const [notes, setNotes] = useState("");
  const set = (k) => (v) => setValues((s) => ({ ...s, [k]: v }));

  const submit = (e) => {
    e.preventDefault();
    const required = country === "us" ? values.baseSalary : values.ctc;
    if (!required) return toast.error(country === "us" ? "Enter the base salary to decode." : "Enter the total CTC to decode.");
    const input = { ...values };
    if (country === "us" && state) input.state = state;
    onSubmit({ input, notes, clauseFlags: prefill?.clauseFlags || [], source: prefill?.beta ? "quickscan" : "manual", country });
  };

  const compact = (v) => (country === "us" ? kfmt(v) : lakhs(v));

  return (
    <form className="card fade-up" onSubmit={submit} data-testid="manual-mode-panel">
      <h2 className="font-display text-lg font-bold text-[var(--text)]">
        {country === "us" ? "Enter the numbers (annual $)" : "Enter the numbers (annual ₹)"}
      </h2>
      {prefill?.beta && (
        <div className="mt-4 rounded-xl border border-amber-500/30 bg-amber-500/[0.07] p-3.5 text-sm text-[var(--warn-text)]" data-testid="quickscan-beta-banner">
          <p className="flex items-center gap-2 font-semibold"><FlaskConical size={15} className="text-[var(--warn-strong)]" /> Quick scan · Beta - verify every number</p>
          <p className="mt-1 text-xs opacity-80">Pre-filled from your text by pattern matching, without AI. Found: {Object.keys(prefill.fields || {}).length} values{prefill.clauseFlags?.length ? `, ${prefill.clauseFlags.length} clause flags` : ""}.</p>
          {prefill.scanNotes?.map((n) => <p key={n} className="mt-1 text-xs opacity-70">• {n}</p>)}
        </div>
      )}
      <div className="mt-5 grid grid-cols-1 sm:grid-cols-2 gap-x-4 gap-y-5">
        {FIELDS.map((f) => (
          <div key={f.key} className={f.key === "ctc" || f.key === "baseSalary" ? "sm:col-span-2" : ""}>
            <label htmlFor={`m-${f.key}`} className="flex items-baseline justify-between text-sm font-semibold text-[var(--text-2)]">
              {f.label}
              {values[f.key] ? <span className="font-num text-xs text-[var(--accent-text)] opacity-80">{compact(values[f.key])}</span> : null}
            </label>
            <div className="mt-1.5">
              <AmountInput id={`m-${f.key}`} country={country} value={values[f.key]} onChange={set(f.key)} placeholder={f.key === "ctc" ? "18,00,000" : f.key === "baseSalary" ? "145,000" : "Leave blank to assume"} testId={`manual-${f.key}-input`} />
            </div>
            <p className="mt-1 text-[11px] text-[var(--text-faint)]">{f.hint}</p>
          </div>
        ))}
        {country === "us" && (
          <div className="sm:col-span-2">
            <label htmlFor="m-state" className="text-sm font-semibold text-[var(--text-2)]">Work state</label>
            <select id="m-state" className="field mt-1.5 text-sm" value={state} onChange={(e) => setState(e.target.value)} data-testid="manual-state-select">
              <option value="">Choose a state (for state tax)…</option>
              {US_STATES.map((s) => (
                <option key={s.code} value={s.code}>{s.name}{s.noTax ? " - no income tax" : ""}</option>
              ))}
            </select>
            <p className="mt-1 text-[11px] text-[var(--text-faint)]">Estimates assume a single filer taking the standard deduction. City/local taxes not included.</p>
          </div>
        )}
        <div className="sm:col-span-2">
          <label htmlFor="m-notes" className="text-sm font-semibold text-[var(--text-2)]">Notes (clauses, bond, notice period…)</label>
          <textarea id="m-notes" rows={3} className="field mt-1.5 text-sm" value={notes} onChange={(e) => setNotes(e.target.value)} placeholder={country === "us" ? "e.g. signing bonus repayable within 12 months, 1-year vesting cliff" : "e.g. 2-year service bond of Rs 2 lakh, notice period 90 days"} data-testid="manual-notes-textarea" />
          <p className="mt-1 text-[11px] text-[var(--text-faint)]">Scanned offline for risky clauses - no AI.</p>
        </div>
      </div>
      <button type="submit" className="btn-accent mt-6 w-full sm:w-auto" data-testid="manual-decode-button">
        Decode my offer <ArrowRight size={16} />
      </button>
    </form>
  );
};
