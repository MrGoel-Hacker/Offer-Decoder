import { useState } from "react";
import { Check, Copy, Link2, Save } from "lucide-react";
import { toast } from "sonner";
import { http, errMsg, toPayload } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { AuthModal } from "@/components/AuthModal";
import { PackCard } from "@/components/report/PackCard";

export const ShareBar = ({ session, input }) => {
  const { user, authHeaders } = useAuth();
  const [savedId, setSavedId] = useState("");
  const [url, setUrl] = useState("");
  const [busy, setBusy] = useState(false);
  const [sharing, setSharing] = useState(false);
  const [copied, setCopied] = useState(false);
  const [showAuth, setShowAuth] = useState(false);

  const save = async () => {
    setBusy(true);
    try {
      const { data } = await http.post("/reports", {
        input: toPayload(input), clauseFlags: session.clauseFlags || [], notes: session.notes || "",
        company: session.company || "", role: session.role || "", source: session.source || "manual", country: session.country || "in",
      }, { headers: authHeaders() });
      setSavedId(data.id);
      toast.success("Saved to My reports - only you can see it.");
    } catch (e) {
      toast.error(errMsg(e));
    } finally {
      setBusy(false);
    }
  };

  const share = async () => {
    setSharing(true);
    try {
      await http.post(`/reports/${savedId}/share`, {}, { headers: authHeaders() });
      setUrl(`${window.location.origin}/r/${savedId}`);
    } catch (e) {
      toast.error(errMsg(e));
    } finally {
      setSharing(false);
    }
  };

  const onSaveClick = () => {
    if (!user) {
      setShowAuth(true);
      return;
    }
    save();
  };

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(url);
      setCopied(true);
      setTimeout(() => setCopied(false), 1800);
    } catch {
      toast.error("Couldn't copy - select the link and copy it manually.");
    }
  };

  return (
    <section className="card fade-up border-emerald-500/25" data-testid="share-bar">
      <h2 className="font-display text-xl font-bold text-[var(--text)]">Save this report</h2>
      <p className="mt-1 text-sm text-[var(--text-dim)]">
        Saved reports are private to your account and expire after 90 days. Want to send it to someone? Create a share link after saving - only then can anyone with the link view it, no login needed.
      </p>
      {url ? (
        <div className="mt-4">
          <p className="mb-2 text-xs font-semibold text-[var(--accent-text)]">Share link created - anyone with this link can view the report.</p>
          <div className="flex gap-2">
            <input readOnly value={url} className="field font-num text-xs" onFocus={(e) => e.target.select()} data-testid="share-url-input" />
            <button type="button" onClick={copy} className="btn-accent !px-4 shrink-0" data-testid="share-copy-button">
              {copied ? <Check size={16} /> : <Copy size={16} />}
            </button>
          </div>
        </div>
      ) : savedId ? (
        <div className="mt-4">
          <p className="text-xs font-semibold text-emerald-500" data-testid="saved-confirmation">Saved to My reports.</p>
          <button type="button" onClick={share} disabled={sharing} className="btn-accent mt-3" data-testid="create-share-link-button">
            <Link2 size={16} /> {sharing ? "Creating link…" : "Create share link"}
          </button>
        </div>
      ) : (
        <button type="button" onClick={onSaveClick} disabled={busy} className="btn-accent mt-4" data-testid="save-report-button">
          <Save size={16} /> {busy ? "Saving…" : "Save report"}
        </button>
      )}
      {savedId && <PackCard reportId={savedId} />}
      <AuthModal
        open={showAuth}
        onClose={() => setShowAuth(false)}
        onDone={() => { setShowAuth(false); save(); }}
        title="Sign in to save your report"
        subtitle="Your decoded result stays exactly as it is. Sign in, and we save it straight away - private to your account."
      />
    </section>
  );
};
