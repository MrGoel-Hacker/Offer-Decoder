import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { RotateCcw } from "lucide-react";
import { http, toPayload } from "@/lib/api";
import { Headline } from "@/components/report/Headline";
import { Breakdown } from "@/components/report/Breakdown";
import { TaxPanel } from "@/components/report/TaxPanel";
import { Assumptions } from "@/components/report/Assumptions";
import { Flags } from "@/components/report/Flags";
import { Tips } from "@/components/report/Tips";
import { ShareBar } from "@/components/report/ShareBar";

const SOURCE = { ai: "Read by AI", quickscan: "Quick scan · Beta", manual: "Manual entry" };

const ReportTop = ({ session, onReset, readOnly, expiresAt }) => (
  <div className="flex flex-wrap items-end justify-between gap-4 pt-8 sm:pt-12">
    <div>
      <p className="eyebrow">{readOnly ? "Shared report" : "Your decoded offer"} · {SOURCE[session.source] || "Manual entry"}</p>
      <h1 className="mt-2 font-display text-3xl sm:text-4xl font-extrabold tracking-tight text-slate-50" data-testid="report-title">
        {session.role || session.company ? [session.role, session.company].filter(Boolean).join(" @ ") : "Offer report"}
      </h1>
      {expiresAt && <p className="mt-1 text-xs text-slate-500" data-testid="report-expiry">Link valid until {new Date(expiresAt).toLocaleDateString("en-IN", { day: "numeric", month: "short", year: "numeric" })}</p>}
    </div>
    {readOnly ? (
      <Link to="/" className="btn-ghost !py-2.5" data-testid="decode-own-link">Decode your own offer</Link>
    ) : (
      <button type="button" onClick={onReset} className="btn-ghost !py-2.5" data-testid="start-over-button"><RotateCcw size={15} /> Start over</button>
    )}
  </div>
);

export const ReportView = ({ session, onReset, readOnly, stored, expiresAt }) => {
  const [input, setInput] = useState(session.input);
  const [result, setResult] = useState(stored || null);
  const [syncing, setSyncing] = useState(false);
  const seq = useRef(0);

  useEffect(() => {
    if (readOnly) return;
    const my = ++seq.current;
    setSyncing(true);
    const t = setTimeout(async () => {
      try {
        const { data } = await http.post("/decode", { input: toPayload(input), clauseFlags: session.clauseFlags || [], notes: session.notes || "" });
        if (my === seq.current) setResult(data);
      } finally {
        if (my === seq.current) setSyncing(false);
      }
    }, 250);
    return () => clearTimeout(t);
  }, [input, readOnly, session.clauseFlags, session.notes]);

  const set = (k, v) => setInput((s) => ({ ...s, [k]: v }));

  return (
    <div className="pb-6" data-testid="report-view">
      <ReportTop session={session} onReset={onReset} readOnly={readOnly} expiresAt={expiresAt} />
      {!result ? (
        <p className="mt-10 text-sm text-slate-500" data-testid="report-loading">Crunching the numbers…</p>
      ) : (
        <div className={`mt-8 space-y-6 ${syncing ? "opacity-90" : ""}`} style={{ transition: "opacity .2s" }}>
          <Headline r={result} />
          <Breakdown r={result} />
          <TaxPanel r={result} />
          <Assumptions r={result} input={input} onChange={set} readOnly={readOnly} />
          <Flags flags={result.flags} />
          <Tips tips={result.tips} />
          {!readOnly && <ShareBar session={session} input={input} />}
        </div>
      )}
    </div>
  );
};
