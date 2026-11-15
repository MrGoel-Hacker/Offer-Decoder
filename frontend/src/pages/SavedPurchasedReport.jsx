import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { http, errMsg } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { AuthModal } from "@/components/AuthModal";
import { ReportView } from "@/components/report/ReportView";
import { PurchasedReportActions } from "@/components/PurchasedReportActions";

export default function SavedPurchasedReport() {
  const { id } = useParams();
  const { user, ready, authHeaders } = useAuth();
  const [doc, setDoc] = useState(null);
  const [error, setError] = useState("");
  const [showAuth, setShowAuth] = useState(false);
  useEffect(() => {
    if (!ready) return;
    let stopped = false;
    setError(""); setDoc(null);
    http.get(`/payments/reports/${id}`, { headers: authHeaders() }).then(({ data }) => { if (!stopped) setDoc(data); })
      .catch((e) => { if (!stopped) setError(errMsg(e, "Couldn't open this report. Please retry.")); });
    return () => { stopped = true; };
  }, [id, user, ready, authHeaders]);
  return <main className="max-w-3xl mx-auto px-5 ph-no-capture" data-clarity-mask="true">
    {error ? <div className="card mt-8 space-y-4"><p role="alert">{error}</p>{!user && <button className="btn-accent" onClick={() => setShowAuth(true)}>Sign in to view your private report</button>}<Link className="btn-ghost" to="/my/reports">My Reports</Link></div>
      : !doc ? <p className="py-12">Verifying report access…</p> : <>{doc.freeReport && <p className="mt-6 text-sm text-[var(--accent-text)]">Your free full report · Saved in My Reports · No payment needed</p>}<PurchasedReportActions reportId={id} shared={doc.shared} allowShare={doc.canShare} /><ReportView readOnly session={doc.session} stored={doc.result} expiresAt={doc.expiresAt} /></>}
    <AuthModal open={showAuth} onClose={() => setShowAuth(false)} />
  </main>;
}
