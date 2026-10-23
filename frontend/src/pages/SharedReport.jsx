import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { http, errMsg } from "@/lib/api";
import { ReportView } from "@/components/report/ReportView";

export default function SharedReport() {
  const { id } = useParams();
  const [doc, setDoc] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    http.get(`/reports/${id}`).then((r) => setDoc(r.data)).catch((e) => setError(errMsg(e, "Report not found or expired.")));
  }, [id]);

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
