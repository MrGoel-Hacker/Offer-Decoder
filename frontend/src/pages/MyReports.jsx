import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Check, Copy, FileText, Link2, Trash2 } from "lucide-react";
import { toast } from "sonner";
import { http, errMsg } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { AuthModal } from "@/components/AuthModal";

const fmt = (iso) => new Date(iso).toLocaleDateString("en-IN", { day: "numeric", month: "short", year: "numeric" });

const MyReports = () => {
  const { user, ready, authHeaders } = useAuth();
  const navigate = useNavigate();
  const [items, setItems] = useState(null);
  const [showAuth, setShowAuth] = useState(false);

  const load = () => {
    http.get("/my/reports", { headers: authHeaders() })
      .then(({ data }) => setItems(data.reports))
      .catch((e) => { toast.error(errMsg(e)); setItems([]); });
  };

  useEffect(() => {
    if (!ready) return;
    if (!user) { setShowAuth(true); return; }
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [ready, user]);

  const [copiedId, setCopiedId] = useState("");

  const share = async (id) => {
    try {
      await http.post(`/reports/${id}/share`, {}, { headers: authHeaders() });
      setItems((xs) => xs.map((x) => (x.id === id ? { ...x, shared: true } : x)));
      toast.success("Share link created - anyone with the link can now view it.");
    } catch (e) {
      toast.error(errMsg(e));
    }
  };

  const copyLink = async (id) => {
    try {
      await navigator.clipboard.writeText(`${window.location.origin}/r/${id}`);
      setCopiedId(id);
      setTimeout(() => setCopiedId(""), 1800);
    } catch {
      toast.error("Couldn't copy - select the link and copy it manually.");
    }
  };

  const del = async (id) => {
    try {
      await http.delete(`/my/reports/${id}`, { headers: authHeaders() });
      setItems((xs) => xs.filter((x) => x.id !== id));
      toast.success("Report deleted.");
    } catch (e) {
      toast.error(errMsg(e));
    }
  };

  return (
    <main className="max-w-3xl mx-auto px-5 py-10">
      <p className="eyebrow">Your account</p>
      <h1 className="font-display text-3xl font-extrabold text-[var(--text)]">My reports</h1>
      <p className="mt-2 text-sm text-[var(--text-dim)]">Reports you have saved are private to you. Create a share link only if you want someone else to view one. Reports expire after 90 days.</p>

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
            <li key={r.id} className="card flex items-center justify-between gap-3 !py-4">
              <Link to={`/r/${r.id}`} className="flex min-w-0 items-center gap-3" data-testid={`report-link-${r.id.slice(0, 6)}`}>
                <FileText size={18} className="shrink-0 text-[var(--accent-text)]" />
                <span className="min-w-0">
                  <span className="block truncate font-semibold text-[var(--text)]">{r.company || "Untitled offer"}{r.role ? ` · ${r.role}` : ""}</span>
                  <span className="block text-xs text-[var(--text-dim)]">Saved {fmt(r.createdAt)} · expires {fmt(r.expiresAt)}{r.shared ? " · link shared" : " · private"}</span>
                </span>
              </Link>
              {r.shared ? (
                <button type="button" onClick={() => copyLink(r.id)} aria-label="Copy share link" className="shrink-0 text-[var(--text-dim)] hover:text-[var(--accent-text)]" data-testid={`copy-link-${r.id.slice(0, 6)}`}>
                  {copiedId === r.id ? <Check size={16} /> : <Copy size={16} />}
                </button>
              ) : (
                <button type="button" onClick={() => share(r.id)} aria-label="Create share link" className="shrink-0 text-[var(--text-dim)] hover:text-[var(--accent-text)]" data-testid={`share-${r.id.slice(0, 6)}`}>
                  <Link2 size={16} />
                </button>
              )}
              <button type="button" onClick={() => del(r.id)} aria-label="Delete report" className="shrink-0 text-[var(--text-dim)] hover:text-red-400" data-testid={`delete-report-${r.id.slice(0, 6)}`}>
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
