import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { http, errMsg } from "@/lib/api";
import { ReportView } from "@/components/report/ReportView";

export default function PurchasedReport() {
  const { token } = useParams();
  const [doc, setDoc] = useState(null);
  const [error, setError] = useState("");
  const [attempt, setAttempt] = useState(0);
  useEffect(() => {
    let stopped = false;
    let timer;
    let checks = 0;
    setError("");
    setDoc(null);
    async function check() {
      try {
        const { data } = await http.get(`/payments/orders/${token}`);
        if (stopped) return;
        setDoc(data);
        if (data.status === "pending" && ++checks < 12) timer = setTimeout(check, 5000);
      } catch (e) {
        if (!stopped) setError(errMsg(e, "Couldn't verify payment. Keep this link and retry."));
      }
    }
    check();
    return () => { stopped = true; clearTimeout(timer); };
  }, [token, attempt]);
  const checkoutUrl = sessionStorage.getItem(`offerdecode:checkout:${token}`);
  if (doc?.status === "paid") return <main data-clarity-mask="true" className="max-w-3xl mx-auto px-5 ph-no-capture"><p className="mt-6 text-sm text-[var(--accent-text)]">Payment verified · Bookmark this private link to reopen your report.</p><ReportView readOnly session={doc.session} stored={doc.result} expiresAt={doc.expiresAt} /></main>;
  return <main className="max-w-3xl mx-auto px-5 py-12 space-y-5">
    <h1 className="text-3xl font-display font-bold">{doc?.status === "review_required" ? "Payment needs review" : doc?.status === "failed" ? "Payment wasn't completed" : "Verifying your payment"}</h1>
    <p className="text-[var(--text-dim)]">{error || (doc?.status === "review_required" ? "This payment doesn't currently grant access. It may have been refunded or disputed, or its details may not match the order. Don't pay again; contact the website owner with your Dodo receipt." : "Your report unlocks after payment is confirmed. If you have already paid, don't pay again; retry verification.")}</p>
    <button className="btn-primary" onClick={() => setAttempt((n) => n + 1)}>Check payment again</button>
    {checkoutUrl && doc?.status !== "review_required" && <a className="block text-[var(--accent-text)]" href={checkoutUrl}>Return to checkout if you haven't paid</a>}
    <Link to="/" className="block text-[var(--text-dim)]">Back to Offer Decoder</Link>
  </main>;
}
