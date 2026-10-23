import { useState } from "react";
import { ChevronDown } from "lucide-react";
import { Switch } from "@/components/ui/switch";
import { AmountInput } from "@/components/AmountInput";
import { fieldsFor } from "@/lib/fields";
import { US_STATES } from "@/lib/states";
import { money } from "@/lib/format";

const ROWS_IN = [
  { key: "basic", label: "Basic salary", match: /^Basic/, std: "From your input" },
  { key: "employerPF", label: "Employer PF", match: /^Employer PF/, std: "From your input" },
  { key: "gratuity", label: "Gratuity", match: /^Gratuity/, std: "From your input" },
  { key: "employeePF", dKey: "employeePF", label: "Your PF deduction", std: "12% of basic unless you change it" },
  { key: "profTax", dKey: "profTax", label: "Professional tax", std: "Typical state amount ₹2,400/yr unless you change it" },
];

const ROWS_US = [
  { key: "k401", label: "Your 401(k) contribution", std: "Blank = none; capped at the 2026 limit of $24,500" },
];

const AssumptionRow = ({ row, r, input, onChange, readOnly, country }) => {
  const fmt = money(country);
  const assumed = row.match && r.assumptions.find((a) => row.match.test(a));
  return (
    <div className="grid grid-cols-1 sm:grid-cols-[1fr_200px] items-center gap-3 border-t border-[var(--line)] py-4" data-testid={`assumption-row-${row.key}`}>
      <div>
        <p className="flex items-center gap-2 text-sm font-semibold text-[var(--text-2)]">
          {row.label}
          {assumed && <span className="rounded-full border border-amber-500/30 bg-amber-500/10 px-2 py-0.5 text-[10px] font-bold uppercase tracking-wide text-[var(--warn-strong)]">Assumed</span>}
        </p>
        <p className="mt-0.5 text-xs text-[var(--text-faint)]">{assumed || row.std}</p>
      </div>
      {readOnly ? (
        <p className="font-num text-right text-[var(--text)]">{fmt(r.derived[row.dKey || row.key])}</p>
      ) : (
        <AmountInput country={country} value={input[row.key] ?? ""} onChange={(v) => onChange(row.key, v)} placeholder={String(fmt(r.derived[row.dKey || row.key])).replace(/[₹$]/, "")} testId={`assumption-${row.key}-input`} />
      )}
    </div>
  );
};

const StateRow = ({ r, input, onChange, readOnly }) => (
  <div className="grid grid-cols-1 sm:grid-cols-[1fr_200px] items-center gap-3 border-t border-[var(--line)] py-4" data-testid="assumption-row-state">
    <div>
      <p className="flex items-center gap-2 text-sm font-semibold text-[var(--text-2)]">
        Work state
        {!input.state && <span className="rounded-full border border-amber-500/30 bg-amber-500/10 px-2 py-0.5 text-[10px] font-bold uppercase tracking-wide text-[var(--warn-strong)]">Assumed</span>}
      </p>
      <p className="mt-0.5 text-xs text-[var(--text-faint)]">
        {input.state ? `${r.stateName || input.state} state tax included (estimate).` : "No state selected - federal + FICA only."}
      </p>
    </div>
    {readOnly ? (
      <p className="font-num text-right text-[var(--text)]">{r.stateName || "-"}</p>
    ) : (
      <select className="field text-sm" value={input.state || ""} onChange={(e) => onChange("state", e.target.value)} data-testid="assumption-state-select">
        <option value="">No state</option>
        {US_STATES.map((s) => (
          <option key={s.code} value={s.code}>{s.name}{s.noTax ? " - no income tax" : ""}</option>
        ))}
      </select>
    )}
  </div>
);

const AllInputs = ({ input, onChange, country }) => {
  const [open, setOpen] = useState(false);
  const skip = country === "us" ? [] : ["basic", "employerPF", "gratuity"];
  return (
    <div className="mt-4">
      <button type="button" onClick={() => setOpen(!open)} className="flex items-center gap-2 text-sm font-semibold text-[var(--accent-text)]" data-testid="toggle-all-inputs">
        <ChevronDown size={16} style={{ transform: open ? "rotate(180deg)" : "none", transition: "transform .2s" }} /> Edit all offer numbers
      </button>
      {open && (
        <div className="mt-4 grid grid-cols-1 sm:grid-cols-2 gap-4" data-testid="all-inputs-editor">
          {fieldsFor(country).filter((f) => !skip.includes(f.key) && f.key !== "k401").map((f) => (
            <div key={f.key}>
              <p className="mb-1.5 text-xs font-semibold text-[var(--text-2)]">{f.label}</p>
              <AmountInput country={country} value={input[f.key] ?? ""} onChange={(v) => onChange(f.key, v)} placeholder="0" testId={`edit-${f.key}-input`} />
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export const Assumptions = ({ r, input, onChange, readOnly }) => {
  const country = r.country || "in";
  const ROWS = country === "us" ? ROWS_US : ROWS_IN;
  return (
    <section className="card fade-up" data-testid="assumptions-panel">
      <h2 className="font-display text-xl font-bold text-[var(--text)]">Assumptions</h2>
      <p className="mt-1 text-sm text-[var(--text-faint)]">{readOnly ? "Values used in this report." : "Change any value - the report recalculates instantly. Clear a box to go back to the assumption."}</p>
      <div className="mt-4">
        {ROWS.map((row) => <AssumptionRow key={row.key} row={row} r={r} input={input} onChange={onChange} readOnly={readOnly} country={country} />)}
        {country === "us" && <StateRow r={r} input={input} onChange={onChange} readOnly={readOnly} />}
        {country !== "us" && !readOnly && (
          <label className="flex items-center justify-between gap-4 border-t border-[var(--line)] pt-4 text-sm text-[var(--text-2)]">
            Gratuity is part of my CTC
            <Switch checked={input.gratuityInCTC !== false} onCheckedChange={(c) => onChange("gratuityInCTC", c ? "" : false)} data-testid="gratuity-in-ctc-switch" />
          </label>
        )}
      </div>
      {!readOnly && <AllInputs input={input} onChange={onChange} country={country} />}
    </section>
  );
};
