import { useCallback, useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { Check, Copy } from "lucide-react";
import { toast } from "sonner";
import { http, errMsg } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { AuthModal } from "@/components/AuthModal";

const CopyBlock = ({ label, text }) => {
  const [done, setDone] = useState(false);
  const copy = async () => {
    try {
      await navigator.clipboard.writeText(text);
      setDone(true);
      setTimeout(() => setDone(false), 1600);
    } catch {
      toast.error("Couldn't copy - select the text and copy it manually.");
    }
  };
  return (
    <div className="mt-3">
      <div className="mb-1 flex items-center justify-between">
        <span className="text-xs font-semibold text-[var(--text-dim)]">{label}</span>
        <button type="button" onClick={copy} className="text-xs text-[var(--accent-text)] flex items-center gap-1">
          {done ? <Check size={14} /> : <Copy size={14} />} {done ? "Copied" : "Copy"}
        </button>
      </div>
      <pre className="field whitespace-pre-wrap text-xs !h-auto">{text}</pre>
    </div>
  );
};

const Section = ({ title, children }) => (
  <section className="card mt-6">
    <h2 className="font-display text-xl font-bold text-[var(--text)]">{title}</h2>
    {children}
  </section>
);

const Pack = () => {
  const { id } = useParams();
  const fromCheckout = new URLSearchParams(window.location.search).get("from") === "checkout";
  const [buying, setBuying] = useState(false);
  const { user, ready, authHeaders } = useAuth();
  const [showAuth, setShowAuth] = useState(false);
  const [pack, setPack] = useState(null);
  const [status, setStatus] = useState("loading"); // loading | ok | locked | error
  const [attempt, setAttempt] = useState(0);
  const [askPct, setAskPct] = useState(10);
  const [others, setOthers] = useState([]);
  const [cmp, setCmp] = useState(null);

  const load = useCallback(async (pct) => {
    try {
      const { data } = await http.post("/pack/negotiation", { reportId: id, askPct: pct }, { headers: authHeaders() });
      setPack(data);
      setStatus("ok");
    } catch (e) {
      const code = e?.response?.status;
      setStatus(code === 402 || code === 503 ? "locked" : "error");
    }
  }, [id]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (!ready) return;
    if (!user) { setShowAuth(true); return; }
    load(askPct);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [ready, user, id, attempt]);

  // The payment webhook can arrive a few seconds after the redirect back from checkout.
  useEffect(() => {
    if (!fromCheckout || status !== "locked" || attempt >= 4) return undefined;
    const t = setTimeout(() => setAttempt((n) => n + 1), 3000);
    return () => clearTimeout(t);
  }, [status, attempt, fromCheckout]);

  useEffect(() => {
    if (status !== "ok") return;
    http.get("/my/reports", { headers: authHeaders() })
      .then(({ data }) => setOthers(data.reports.filter((r) => r.id !== id)))
      .catch(() => {});
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [status]);

  const compare = async (otherId) => {
    try {
      const { data } = await http.post("/pack/compare", { reportIdA: id, reportIdB: otherId }, { headers: authHeaders() });
      setCmp(data);
    } catch (e) {
      toast.error(errMsg(e));
    }
  };

  const unlock = async () => {
    setBuying(true);
    try {
      const { data } = await http.post("/payments/checkout", { reportId: id }, { headers: authHeaders() });
      window.location.href = data.checkoutUrl;
    } catch (e) {
      toast.error(errMsg(e, "Couldn't start checkout. Please try again."));
      setBuying(false);
    }
  };

  const fmtMoney = (c, n) => (c === "us" ? `$${Math.round(n).toLocaleString("en-US")}` : `₹${Math.round(n).toLocaleString("en-IN")}`);

  return (
    <main className="max-w-3xl mx-auto px-5 py-10" data-testid="pack-page">
      <p className="eyebrow">Offer Pack</p>
      <h1 className="font-display text-3xl font-extrabold text-[var(--text)]">Negotiation guidance</h1>
      <p className="mt-2 text-sm text-[var(--text-dim)]">
        Built from the numbers in your saved report. These are what-if scenarios, not market salary data, and nobody can promise a company will agree to any figure.
      </p>

      {status === "loading" && <p className="mt-8 text-sm text-[var(--text-dim)]">Loading…</p>}
      {status === "locked" && (
        <div className="card mt-8" data-testid="pack-locked">
          {fromCheckout && attempt < 4 ? (
            <p className="text-sm text-[var(--text-dim)]">Checking your payment…</p>
          ) : (
            <>
              <p className="text-sm text-[var(--text-dim)]">
                {fromCheckout
                  ? "We haven't received your payment confirmation yet. It can take a minute."
                  : "The Offer Pack isn't unlocked for this report yet."}
              </p>
              <div className="mt-3 flex flex-wrap gap-3">
                {fromCheckout && (
                  <button type="button" className="btn-ghost" onClick={() => { setStatus("loading"); setAttempt(0); }}>Check again</button>
                )}
                <button type="button" className="btn-accent" disabled={buying} onClick={unlock} data-testid="pack-unlock-button">
                  {buying ? "Opening checkout…" : "Unlock Offer Pack"}
                </button>
                <Link to="/my/reports" className="btn-ghost">My reports</Link>
              </div>
              <p className="mt-3 text-xs text-[var(--text-faint)]">One-time purchase for this report. The price is shown at checkout. Payment is handled by Dodo Payments.</p>
            </>
          )}
        </div>
      )}
      {status === "error" && <p className="mt-8 text-sm text-red-400">Couldn't load this pack. Try again from My reports.</p>}

      {status === "ok" && pack && (
        <>
          <Section title="Where to push">
            <ol className="mt-3 list-decimal space-y-2 pl-5 text-sm text-[var(--text)]">
              {pack.priorities.map((p) => <li key={p}>{p}</li>)}
            </ol>
          </Section>

          <Section title="What a raise would do to your take-home">
            <p className="mt-1 text-sm text-[var(--text-dim)]">Current estimated fixed in-hand: {fmtMoney(pack.country, pack.currentMonthlyFixed)} a month.</p>
            <ul className="mt-3 space-y-2 text-sm text-[var(--text)]">
              {pack.scenarios.map((s) => <li key={s.raisePct}>{s.text}</li>)}
            </ul>
          </Section>

          {pack.questions.length > 0 && (
            <Section title="Questions to ask">
              <ul className="mt-3 space-y-4 text-sm">
                {pack.questions.map((q) => (
                  <li key={q.ask}>
                    <p className="font-semibold text-[var(--text)]">{q.ask}</p>
                    <p className="text-xs text-[var(--text-dim)]">Why: {q.why}</p>
                  </li>
                ))}
              </ul>
            </Section>
          )}

          <Section title="Messages you can edit">
            <label className="mt-2 block text-xs text-[var(--text-dim)]">
              Raise to ask for in the draft (percent of fixed pay)
              <input type="number" min="1" max="30" value={askPct} onChange={(e) => setAskPct(e.target.value)} onBlur={() => load(askPct)} className="field ml-2 !w-20 inline-block" />
            </label>
            <CopyBlock label="Email" text={pack.scripts.email} />
            <CopyBlock label="Chat message" text={pack.scripts.chat} />
            <p className="mt-3 text-xs text-[var(--text-faint)]">Fill the [brackets] yourself. The percentage is your choice, not a benchmark.</p>
          </Section>

          <Section title="Compare with another saved report">
            {others.length === 0 ? (
              <p className="mt-2 text-sm text-[var(--text-dim)]">Save a second offer from the same country and it will show up here.</p>
            ) : (
              <ul className="mt-3 space-y-2">
                {others.map((r) => (
                  <li key={r.id}>
                    <button type="button" className="text-sm text-[var(--accent-text)] underline" onClick={() => compare(r.id)}>
                      Compare with {r.company || "Untitled offer"}{r.role ? ` · ${r.role}` : ""}
                    </button>
                  </li>
                ))}
              </ul>
            )}
            {cmp && (
              <div className="mt-5 text-sm text-[var(--text)]" data-testid="pack-compare-result">
                <p className="font-semibold">{cmp.verdict}</p>
                <table className="mt-3 w-full text-left text-xs">
                  <thead><tr className="text-[var(--text-dim)]"><th className="py-1">Offer</th><th>Fixed / month</th><th>With variable / month</th><th>4-year cash (fixed only)</th></tr></thead>
                  <tbody>
                    {cmp.offers.map((o) => (
                      <tr key={o.label}><td className="py-1">{o.label}</td><td>{fmtMoney(cmp.country, o.monthlyFixed)}</td><td>{fmtMoney(cmp.country, o.monthlyWithVariable)}</td><td>{fmtMoney(cmp.country, o.fourYearFixedOnly)}</td></tr>
                    ))}
                  </tbody>
                </table>
                <ul className="mt-3 list-disc space-y-1 pl-5 text-xs text-[var(--text-faint)]">
                  {cmp.caveats.map((c) => <li key={c}>{c}</li>)}
                </ul>
              </div>
            )}
          </Section>
        </>
      )}
      <AuthModal open={showAuth && !user} onClose={() => setShowAuth(false)} title="Sign in to open your Offer Pack" />
    </main>
  );
};

export default Pack;
