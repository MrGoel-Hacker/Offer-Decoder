import { useState } from "react";
import { Link } from "react-router-dom";
import { Download, Link2, Check, FolderOpen } from "lucide-react";
import { toast } from "sonner";
import { http, errMsg } from "@/lib/api";
import { useAuth } from "@/lib/auth";

export async function downloadReport(path, headers) {
  try {
    const { data } = await http.get(path, { headers, responseType: "blob" });
    const url = URL.createObjectURL(data);
    const link = document.createElement("a");
    link.href = url;
    link.download = "OfferDecode-Report.pdf";
    document.body.appendChild(link);
    link.click();
    link.remove();
    setTimeout(() => URL.revokeObjectURL(url), 10000);
  } catch (e) {
    let message = "Couldn't download the PDF. Please try again.";
    try { message = JSON.parse(await e.response.data.text()).detail || message; } catch { /* network error */ }
    throw new Error(message);
  }
}

export function PurchasedReportActions({ reportId, token, shared: initiallyShared = false, allowShare = false }) {
  const { authHeaders } = useAuth();
  const [busy, setBusy] = useState(false);
  const [copied, setCopied] = useState(false);
  const [shared, setShared] = useState(initiallyShared);
  const [shareUrl, setShareUrl] = useState("");
  async function download() {
    setBusy(true);
    try { await downloadReport(token ? `/payments/orders/${token}/pdf` : `/payments/reports/${reportId}/pdf`, authHeaders()); }
    catch (e) { toast.error(e.message); }
    finally { setBusy(false); }
  }
  async function share() {
    try {
      if (!shared) await http.post(`/payments/reports/${reportId}/share`, {}, { headers: authHeaders() });
      setShared(true);
      const url = `${window.location.origin}/paid-report/${reportId}`;
      setShareUrl(url);
      await navigator.clipboard.writeText(url);
      setCopied(true);
      toast.success("Share link copied. Anyone with this link can view your report.");
    } catch (e) { toast.error(errMsg(e, "Couldn't copy the link. If it was created, copy it below.")); }
  }
  return <section className="card mt-6 space-y-4" data-testid="purchased-report-actions">
    <div><h2 className="font-display text-xl font-bold text-[var(--text)]">Your report is ready</h2><p className="mt-1 text-sm text-[var(--text-dim)]">Keep a PDF copy. Your online report is available for 90 days.</p></div>
    <div className="flex flex-col gap-3 sm:flex-row sm:flex-wrap">
      <button className="btn-accent" disabled={busy} onClick={download} data-testid="download-report-pdf"><Download size={18} />{busy ? "Preparing PDF…" : "Download full PDF report"}</button>
      {reportId && allowShare && <button className="btn-ghost" onClick={share}>{copied ? <Check size={17} /> : <Link2 size={17} />}{copied ? "Link copied" : shared ? "Copy share link" : "Create & copy share link"}</button>}
      <Link className="btn-ghost" to="/my/reports"><FolderOpen size={17} />My Reports</Link>
    </div>
    {reportId && allowShare && <p className="text-xs text-[var(--text-faint)]">Private in your account until you create a share link. Only share it with people you trust.</p>}
    {shareUrl && <input readOnly aria-label="Report share link" className="field text-xs" value={shareUrl} onFocus={(e) => e.target.select()} />}
  </section>;
}
