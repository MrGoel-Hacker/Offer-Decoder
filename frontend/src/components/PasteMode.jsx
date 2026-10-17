import { useState } from "react";
import { Sparkles, ScanText } from "lucide-react";
import { toast } from "sonner";
import { http, errMsg } from "@/lib/api";
import { fromFields, SAMPLE_LETTER } from "@/lib/fields";
import { AiNotice, Scanning } from "@/components/AiNotice";

export const aiToSession = (res, source) => ({
  input: fromFields(res.fields),
  clauseFlags: res.flags || [],
  company: res.company || "",
  role: res.role || "",
  source,
});

export const runQuickScan = async (text, onQuickScan) => {
  const { data } = await http.post("/quickscan", { text });
  if (!data.found.length) toast.warning("Quick scan found no amounts - fill the form by hand.");
  onQuickScan({ fields: data.fields, clauseFlags: data.flags, scanNotes: data.notes, beta: true });
};

export const PasteMode = ({ onDecoded, onQuickScan }) => {
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState("");

  const decodeAi = async () => {
    setBusy(true);
    setNotice("");
    try {
      const { data } = await http.post("/extract/text", { text });
      if (data.ok) onDecoded(aiToSession(data, "ai"));
      else setNotice(data.message);
    } catch (e) {
      toast.error(errMsg(e));
    } finally {
      setBusy(false);
    }
  };

  const scan = () => runQuickScan(text, onQuickScan).catch((e) => toast.error(errMsg(e)));

  return (
    <div className="card fade-up" data-testid="paste-mode-panel">
      <div className="flex items-center justify-between gap-3">
        <label htmlFor="offer-text" className="font-display text-lg font-bold text-slate-100">Paste your offer letter</label>
        <button type="button" className="text-xs font-semibold text-emerald-400 hover:underline" onClick={() => setText(SAMPLE_LETTER)} data-testid="paste-sample-button">
          Try a sample
        </button>
      </div>
      <textarea
        id="offer-text"
        rows={9}
        className="field mt-4 resize-y text-sm leading-relaxed"
        placeholder="Dear …, we are pleased to offer you… CTC Rs 18,00,000 per annum…"
        value={text}
        onChange={(e) => setText(e.target.value)}
        data-testid="offer-paste-textarea"
      />
      <div className="mt-4 flex flex-col sm:flex-row gap-3">
        <button type="button" className="btn-accent" disabled={busy || text.trim().length < 40} onClick={decodeAi} data-testid="paste-decode-ai-button">
          <Sparkles size={16} /> Decode with AI
        </button>
        <button type="button" className="btn-ghost" disabled={busy || !text.trim()} onClick={scan} data-testid="paste-quick-scan-button">
          <ScanText size={16} /> Quick scan <span className="text-[10px] uppercase tracking-wider text-amber-400">Beta</span>
        </button>
      </div>
      <p className="mt-3 text-xs text-slate-500">Quick scan runs offline (no AI) and pre-fills the form for you to verify.</p>
      {busy && <Scanning />}
      {notice && (
        <AiNotice message={notice}>
          <button type="button" className="btn-ghost !py-2 !px-4" onClick={scan} data-testid="notice-quick-scan-button">Quick scan instead</button>
          <button type="button" className="btn-ghost !py-2 !px-4" onClick={() => onQuickScan({})} data-testid="notice-manual-button">Enter manually</button>
        </AiNotice>
      )}
    </div>
  );
};
