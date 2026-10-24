import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Sparkles } from "lucide-react";
import { toast } from "sonner";
import { http, errMsg } from "@/lib/api";
import { useAuth } from "@/lib/auth";

// Offer Pack upsell. Renders nothing unless the backend reports payments as enabled
// (PAYMENTS_ENABLED + Dodo env vars), so it stays invisible until deliberately switched on.
export const PackCard = ({ reportId }) => {
  const { authHeaders } = useAuth();
  const [state, setState] = useState(null); // null = unknown/hidden, {paid}
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    let live = true;
    http.get(`/payments/status/${reportId}`, { headers: authHeaders() })
      .then(({ data }) => live && data.enabled && setState({ paid: !!data.paid }))
      .catch(() => {});
    return () => { live = false; };
  }, [reportId]); // eslint-disable-line react-hooks/exhaustive-deps

  if (!state) return null;

  const buy = async () => {
    setBusy(true);
    try {
      const { data } = await http.post("/payments/checkout", { reportId }, { headers: authHeaders() });
      window.location.href = data.checkoutUrl;
    } catch (e) {
      toast.error(errMsg(e));
      setBusy(false);
    }
  };

  return (
    <div className="mt-6 border-t border-[var(--border)] pt-5" data-testid="pack-card">
      <h3 className="font-display text-lg font-bold text-[var(--text)] flex items-center gap-2"><Sparkles size={16} /> Offer Pack for this report</h3>
      <p className="mt-1 text-sm text-[var(--text-dim)]">
        Negotiation talking points, what-if raises using your own take-home numbers, questions to ask, ready-to-edit email and chat messages, and a side-by-side comparison with a second saved report of the same country.
      </p>
      <p className="mt-2 text-xs text-[var(--text-faint)]">
        Built from the numbers in your offer. It does not use market salary data and cannot promise what a company will agree to.
      </p>
      {state.paid ? (
        <Link to={`/pack/${reportId}`} className="btn-accent mt-4 inline-block" data-testid="open-pack-button">Open Offer Pack</Link>
      ) : (
        <button type="button" onClick={buy} disabled={busy} className="btn-accent mt-4" data-testid="buy-pack-button">
          {busy ? "Opening checkout…" : "Unlock Offer Pack"}
        </button>
      )}
      <p className="mt-2 text-xs text-[var(--text-faint)]">One-time purchase for this report. The price is shown at checkout. Payment is handled by Dodo Payments.</p>
    </div>
  );
};
