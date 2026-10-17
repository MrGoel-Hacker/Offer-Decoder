import { AlertTriangle } from "lucide-react";

export const AiNotice = ({ message, children }) => (
  <div className="mt-5 rounded-xl border border-amber-500/30 bg-amber-500/[0.07] p-4" role="alert" data-testid="ai-notice">
    <div className="flex gap-3">
      <AlertTriangle size={18} className="mt-0.5 shrink-0 text-amber-400" />
      <div className="flex-1">
        <p className="text-sm font-semibold text-amber-200" data-testid="ai-notice-message">{message}</p>
        {children && <div className="mt-3 flex flex-wrap gap-2">{children}</div>}
      </div>
    </div>
  </div>
);

export const Scanning = ({ label = "Reading your letter" }) => (
  <div className="mt-5 flex items-center gap-4 rounded-xl border border-[#1c2536] bg-[#0b111c] p-4" data-testid="ai-loading">
    <div className="relative h-14 w-11 overflow-hidden rounded-md border border-slate-700 bg-[#0f1522]">
      <div className="absolute inset-x-1.5 top-2 space-y-1.5">
        {[80, 60, 90, 50, 70].map((w, i) => (
          <div key={i} className="h-[3px] rounded bg-slate-700" style={{ width: `${w}%` }} />
        ))}
      </div>
      <div className="scanline absolute inset-x-0 -top-2 h-[2px] bg-emerald-400 shadow-[0_0_12px_#10b981]" />
    </div>
    <div>
      <p className="text-sm font-semibold text-slate-100">{label}…</p>
      <p className="text-xs text-slate-500">Free AI models can take 10-40 seconds.</p>
    </div>
  </div>
);
