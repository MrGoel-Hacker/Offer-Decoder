import { group, toNum } from "@/lib/format";

export const AmountInput = ({ id, value, onChange, placeholder, testId, disabled }) => (
  <div className="relative">
    <span className="pointer-events-none absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-500 font-num text-sm">₹</span>
    <input
      id={id}
      inputMode="numeric"
      autoComplete="off"
      className="field font-num pl-8"
      value={group(value)}
      placeholder={placeholder}
      disabled={disabled}
      onChange={(e) => onChange(toNum(e.target.value))}
      data-testid={testId}
    />
  </div>
);
