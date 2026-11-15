import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { RotateCcw } from "lucide-react";
import { http, toPayload, errMsg } from "@/lib/api";
import { Headline } from "@/components/report/Headline";
import { Breakdown } from "@/components/report/Breakdown";
import { TaxPanel } from "@/components/report/TaxPanel";
import { Assumptions } from "@/components/report/Assumptions";
import { Flags } from "@/components/report/Flags";
import { Tips } from "@/components/report/Tips";
import { ShareBar } from "@/components/report/ShareBar";
import { ReportCheckout } from "@/components/ReportCheckout";
import { useAuth } from "@/lib/auth";

const SOURCE = { ai: "Read by AI", quickscan: "Quick scan · Beta", manual: "Manual entry" };

const ReportTop = ({ session, onReset, readOnly, expiresAt }) => (
  <div className="flex flex-wrap items-end justify-between gap-4 pt-8 sm:pt-12">
    <div>
      <p className="eyebrow">{readOnly ? "Shared report" : "Your decoded offer"} · {SOURCE[session.source] || "Manual entry"}</p>
      <h1 className="mt-2 font-display text-3xl sm:text-4xl font-extrabold tracking-tight text-[var(--text)]" data-testid="report-title">
        {session.role || session.company ? [session.role, session.company].filter(Boolean).join(" @ ") : "Offer report"}
      </h1>
      {expiresAt && <p className="mt-1 text-xs text-[var(--text)]0" data-testid="report-expiry">Link valid until {new Date(expiresAt).toLocaleDateString("en-IN", { day: "numeric", month: "short", year: "numeric" })}</p>}
    </div>
    {readOnly ? (
      <Link to="/" className="btn-ghost !py-2.5" data-testid="decode-own-link">Decode your own offer</Link>
    ) : (
      <button type="button" onClick={onReset} className="btn-ghost !py-2.5" data-testid="start-over-button"><RotateCcw size={15} /> Start over</button>
    )}
  </div>
);

const FreeReportView = ({ session, onReset, readOnly, stored, expiresAt }) => {
  const { authHeaders } = useAuth();
  const [input, setInput] = useState(session.input);
  const [result, setResult] = useState(stored || null);
  const [syncing, setSyncing] = useState(false);
  const [error, setError] = useState("");
  const seq = useRef(0);

  useEffect(() => {
    if (readOnly) return;
    const my = ++seq.current;
    setSyncing(true);
    setError("");
    const t = setTimeout(async () => {
      try {
        const { data } = await http.post("/decode", { input: toPayload(input), clauseFlags: session.clauseFlags || [], notes: session.notes || "", country: session.country || "in" }, { headers: authHeaders() });
        if (my === seq.current) setResult(data);
      } catch (e) {
        if (my === seq.current) setError(e?.response?.status === 402
          ? "Report access has changed. Refresh this page to continue to checkout."
          : errMsg(e, "Couldn't calculate your report. Please try again."));
      } finally {
        if (my === seq.current) setSyncing(false);
      }
    }, 250);
    return () => { clearTimeout(t); ++seq.current; };
  }, [input, readOnly, session.clauseFlags, session.notes, session.country, authHeaders]);

  const set = (k, v) => setInput((s) => ({ ...s, [k]: v }));

  return (
    <div className="pb-6" data-testid="report-view">
      <ReportTop session={session} onReset={onReset} readOnly={readOnly} expiresAt={expiresAt} />
      {error && <div role="alert" className="mt-8 space-y-3 text-[var(--text)]">
        <p>{error}</p>
        <button className="btn-ghost" onClick={() => window.location.reload()}>Refresh page</button>
      </div>}
      {!result && !error ? (
        <p className="mt-10 text-sm text-[var(--text)]0" data-testid="report-loading">Crunching the numbers…</p>
      ) : result ? (
        <div className={`mt-8 space-y-6 ${syncing ? "opacity-90" : ""}`} style={{ transition: "opacity .2s" }}>
          <Headline r={result} />
          <Breakdown r={result} />
          <TaxPanel r={result} />
          <Assumptions r={result} input={input} onChange={set} readOnly={readOnly} />
          <Flags flags={result.flags} />
          <Tips tips={result.tips} />
          {!readOnly && <ShareBar session={session} input={input} />}
        </div>
      ) : null}
    </div>
  );
};

export const ReportView = (props) => {
  const [config, setConfig] = useState(null);
  const [error, setError] = useState(false);
  useEffect(() => {
    if (props.readOnly) return;
    http.get(`/payments/config?country=${props.session.country === "us" ? "us" : "in"}`).then(({ data }) => setConfig(data)).catch(() => setError(true));
  }, [props.readOnly, props.session.country]);
  if (props.readOnly) return <FreeReportView {...props} />;
  if (error) return <p className="py-10 text-slate-300">Couldn't load report access. Please refresh and try again.</p>;
  if (!config) return <p className="py-10 text-slate-400">Preparing your report…</p>;
  return config.enabled ? <ReportCheckout session={props.session} onReset={props.onReset} config={config} /> : <FreeReportView {...props} />;
};
