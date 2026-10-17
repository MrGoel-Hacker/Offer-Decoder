import { useState } from "react";
import { Check, Copy, Link2 } from "lucide-react";
import { toast } from "sonner";
import { http, errMsg, toPayload } from "@/lib/api";

export const ShareBar = ({ session, input }) => {
  const [url, setUrl] = useState("");
  const [busy, setBusy] = useState(false);
  const [copied, setCopied] = useState(false);

  const save = async () => {
    setBusy(true);
    try {
      const { data } = await http.post("/reports", {
        input: toPayload(input), clauseFlags: session.clauseFlags || [], notes: session.notes || "",
        company: session.company || "", role: session.role || "", source: session.source || "manual",
      });
      setUrl(`${window.location.origin}/r/${data.id}`);
      toast.success("Report saved - anyone with the link can view it.");
    } catch (e) {
      toast.error(errMsg(e));
    } finally {
      setBusy(false);
    }
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
      <h2 className="font-display text-xl font-bold text-slate-100">Share this report</h2>
      <p className="mt-1 text-sm text-slate-500">Saves a snapshot with a private, hard-to-guess link. No login needed to open it. Links expire after 90 days.</p>
      {url ? (
        <div className="mt-4 flex gap-2">
          <input readOnly value={url} className="field font-num text-xs" onFocus={(e) => e.target.select()} data-testid="share-url-input" />
          <button type="button" onClick={copy} className="btn-accent !px-4 shrink-0" data-testid="share-copy-button">
            {copied ? <Check size={16} /> : <Copy size={16} />}
          </button>
        </div>
      ) : (
        <button type="button" onClick={save} disabled={busy} className="btn-accent mt-4" data-testid="save-report-button">
          <Link2 size={16} /> {busy ? "Saving…" : "Save & get link"}
        </button>
      )}
    </section>
  );
};
