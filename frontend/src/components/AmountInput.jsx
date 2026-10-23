import { group, toNum } from "@/lib/format";

export const AmountInput = ({ id, value, onChange, placeholder, testId, disabled, country = "in" }) => (
  <div className="relative">
    <span className="pointer-events-none absolute left-3.5 top-1/2 -translate-y-1/2 text-[var(--text-faint)] font-num text-sm">{country === "us" ? "$" : "₹"}</span>
    <input
      id={id}
      inputMode="numeric"
      autoComplete="off"
      className="field font-num pl-8"
      value={group(value, country)}
      placeholder={placeholder}
      disabled={disabled}
      onChange={(e) => onChange(toNum(e.target.value))}
      data-testid={testId}
    />
  </div>
);
