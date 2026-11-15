import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Check, Copy, FileText, Link2, Trash2 } from "lucide-react";
import { toast } from "sonner";
import { http, errMsg } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { AuthModal } from "@/components/AuthModal";
import { downloadReport } from "@/components/PurchasedReportActions";
import { Download } from "lucide-react";

const fmt = (iso) => new Date(iso).toLocaleDateString("en-IN", { day: "numeric", month: "short", year: "numeric" });

const MyReports = () => {
  const { user, ready, authHeaders } = useAuth();
  const navigate = useNavigate();
  const [items, setItems] = useState(null);
  const [showAuth, setShowAuth] = useState(false);

  const load = () => {
    Promise.all([http.get("/my/reports", { headers: authHeaders() }), http.get("/payments/my-reports", { headers: authHeaders() })])
      .then(([saved, paid]) => setItems([...paid.data.reports, ...saved.data.reports].sort((a, b) => b.createdAt.localeCompare(a.createdAt))))
      .catch((e) => { toast.error(errMsg(e)); setItems([]); });
  };

  useEffect(() => {
    if (!ready) return;
    if (!user) { setShowAuth(true); return; }
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [ready, user]);

  const [copiedId, setCopiedId] = useState("");
  const [downloading, setDownloading] = useState("");

  const share = async (id, paid) => {
    try {
      await http.post(`${paid ? "/payments" : ""}/reports/${id}/share`, {}, { headers: authHeaders() });
      setItems((xs) => xs.map((x) => (x.id === id ? { ...x, shared: true } : x)));
      toast.success("Share link created - anyone with the link can now view it.");
    } catch (e) {
      toast.error(errMsg(e));
    }
  };

  const copyLink = async (id, paid) => {
    try {
      await navigator.clipboard.writeText(`${window.location.origin}/${paid ? "paid-report" : "r"}/${id}`);
      setCopiedId(id);
      setTimeout(() => setCopiedId(""), 1800);
    } catch {
      toast.error("Couldn't copy - select the link and copy it manually.");
    }
  };

  const del = async (id, paid) => {
    try {
      await http.delete(paid ? `/payments/reports/${id}` : `/my/reports/${id}`, { headers: authHeaders() });
      setItems((xs) => xs.filter((x) => x.id !== id));
      toast.success(paid ? "Report removed from your list." : "Report deleted.");
    } catch (e) {
      toast.error(errMsg(e));
    }
  };

  return (
    <main className="max-w-3xl mx-auto px-5 py-10">
      <p className="eyebrow">Your account</p>
      <h1 className="font-display text-3xl font-extrabold text-[var(--text)]">My reports</h1>
      <p className="mt-2 text-sm text-[var(--text-dim)]">Your free report and verified purchases are saved here. Download the full PDF or create a share link. Reports are private until shared and expire after 90 days.</p>

      {items === null ? (
        <p className="mt-8 text-sm text-[var(--text-dim)]">Loading…</p>
      ) : items.length === 0 ? (
        <div className="card mt-8 text-center">
          <p className="text-sm text-[var(--text-dim)]">No saved reports yet.</p>
          <Link to="/" className="btn-accent mt-4 inline-block" data-testid="decode-first-offer">Decode an offer</Link>
        </div>
      ) : (
        <ul className="mt-8 space-y-3" data-testid="my-reports-list">
          {items.map((r) => (
            <li key={r.id} className="card flex flex-wrap items-center gap-3 !py-4">
              <Link to={`/${r.paid ? "paid-report" : "r"}/${r.id}`} className="flex min-w-0 flex-1 basis-full sm:basis-auto items-center gap-3" data-testid={`report-link-${r.id.slice(0, 6)}`}>
                <FileText size={18} className="shrink-0 text-[var(--accent-text)]" />
                <span className="min-w-0">
                  <span className="block truncate font-semibold text-[var(--text)]">{r.company || "Untitled offer"}{r.role ? ` · ${r.role}` : ""}</span>
                  <span className="block text-xs text-[var(--text-dim)]">{r.freeReport ? "Free report · " : ""}Saved {fmt(r.createdAt)} · expires {fmt(r.expiresAt)}{r.shared ? " · link shared" : " · private"}</span>
                </span>
              </Link>
              {r.paid && <button className="btn-ghost !px-3 !py-2 !text-xs" disabled={downloading === r.id} onClick={async () => {
                setDownloading(r.id);
                try { await downloadReport(`/payments/reports/${r.id}/pdf`, authHeaders()); } catch (e) { toast.error(e.message); }
                finally { setDownloading(""); }
              }}><Download size={16} />{downloading === r.id ? "Preparing…" : "Download PDF"}</button>}
              {r.shared ? (
                <button type="button" onClick={() => copyLink(r.id, r.paid)} aria-label="Copy share link" className="btn-ghost !px-3 !py-2 !text-xs" data-testid={`copy-link-${r.id.slice(0, 6)}`}>
                  {copiedId === r.id ? <Check size={16} /> : <Copy size={16} />} Copy link
                </button>
              ) : (
                <button type="button" onClick={() => share(r.id, r.paid)} aria-label="Create share link" className="btn-ghost !px-3 !py-2 !text-xs" data-testid={`share-${r.id.slice(0, 6)}`}>
                  <Link2 size={16} /> Create share link
                </button>
              )}
              <button type="button" onClick={() => del(r.id, r.paid)} aria-label={r.paid ? "Remove from My Reports" : "Delete report"} className="shrink-0 text-[var(--text-dim)] hover:text-red-400" data-testid={`delete-report-${r.id.slice(0, 6)}`}>
                <Trash2 size={16} />
              </button>
            </li>
          ))}
        </ul>
      )}
      <AuthModal open={showAuth && !user} onClose={() => { setShowAuth(false); if (!user) navigate("/"); }} title="Sign in to see your reports" />
    </main>
  );
};

export default MyReports;
