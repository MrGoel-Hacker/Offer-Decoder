import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { http, errMsg } from "@/lib/api";
import { ReportView } from "@/components/report/ReportView";
import { useAuth } from "@/lib/auth";

export default function SharedReport() {
  const { ready, user, authHeaders } = useAuth();
  const { id } = useParams();
  const [doc, setDoc] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!ready) return;
    let stopped = false;
    setError(""); setDoc(null);
    http.get(`/reports/${id}`, { headers: authHeaders() }).then((r) => { if (!stopped) setDoc(r.data); }).catch((e) => { if (!stopped) setError(errMsg(e, "Report not found or expired.")); });
    return () => { stopped = true; };
  }, [id, ready, user, authHeaders]);

  return (
    <main className="max-w-3xl mx-auto px-5" data-testid="shared-report-page">
      {error && (
        <div className="card mt-10 text-center" data-testid="shared-report-error">
          <p className="font-display text-xl font-bold text-[var(--text)]">{error}</p>
          <Link to="/" className="btn-accent mt-6">Decode an offer</Link>
        </div>
      )}
      {!doc && !error && <p className="mt-16 text-center text-sm text-[var(--text)]0" data-testid="shared-report-loading">Loading report…</p>}
      {doc && <ReportView session={doc} stored={doc.result} readOnly expiresAt={doc.expiresAt} />}
    </main>
  );
}
