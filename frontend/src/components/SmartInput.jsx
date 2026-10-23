import { useRef, useState } from "react";
import { FileUp, ImagePlus, ScanText, Sparkles, X } from "lucide-react";
import { toast } from "sonner";
import { http, errMsg } from "@/lib/api";
import { SAMPLE_LETTER_IN, SAMPLE_LETTER_US } from "@/lib/fields";
import { aiToSession, runQuickScan } from "@/lib/extract";
import { AiNotice, Scanning } from "@/components/AiNotice";

const IMG_TYPES = ["image/jpeg", "image/png", "image/webp"];

export const SmartInput = ({ country, onDecoded, onQuickScan }) => {
  const [text, setText] = useState("");
  const [pdf, setPdf] = useState(null);
  const [images, setImages] = useState([]);
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState(null); // {message, pdfText?}
  const [over, setOver] = useState(false);
  const fileRef = useRef(null);

  const clearFiles = () => { setPdf(null); setImages([]); };
  const resetNotice = () => setNotice(null);

  const takeFiles = (list) => {
    resetNotice();
    const pdfs = list.filter((f) => f.type === "application/pdf" || f.name.toLowerCase().endsWith(".pdf"));
    const imgs = list.filter((f) => IMG_TYPES.includes(f.type));
    const rejected = list.length - pdfs.length - imgs.length;
    if (rejected > 0) toast.warning("Only PDF, JPG, PNG or WEBP files.");
    if (pdfs.length) {
      const f = pdfs[0];
      if (f.size > 10 * 1024 * 1024) return toast.error("PDF is larger than 10 MB.");
      setPdf(f);
      setImages([]);
      setText("");
      if (imgs.length) toast.warning("One PDF at a time - photos were left out.");
    } else if (imgs.length) {
      const good = imgs.filter((f) => f.size <= 5 * 1024 * 1024);
      if (good.length < imgs.length) toast.warning("Each photo must be under 5 MB.");
      setImages((prev) => [...prev, ...good].slice(0, 4));
      setPdf(null);
      setText("");
    }
  };

  const onText = (v) => {
    setText(v);
    if (v.trim()) clearFiles();
    resetNotice();
  };

  const sample = () => onText(country === "us" ? SAMPLE_LETTER_US : SAMPLE_LETTER_IN);

  const decode = async () => {
    setBusy(true);
    resetNotice();
    try {
      let data;
      if (pdf) {
        const fd = new FormData();
        fd.append("file", pdf);
        fd.append("country", country);
        ({ data } = await http.post("/extract/pdf", fd));
      } else if (images.length) {
        const fd = new FormData();
        images.forEach((f) => fd.append("files", f));
        fd.append("country", country);
        ({ data } = await http.post("/extract/images", fd));
      } else {
        ({ data } = await http.post("/extract/text", { text, country }));
      }
      if (data.ok) onDecoded(aiToSession(data, "ai", country));
      else setNotice({ message: data.message, pdfText: data.text || "" });
    } catch (e) {
      toast.error(errMsg(e));
    } finally {
      setBusy(false);
    }
  };

  const scan = () => runQuickScan(text, onQuickScan, country).catch((e) => toast.error(errMsg(e)));
  const scanPdfText = () => runQuickScan(notice.pdfText, onQuickScan, country).catch((e) => toast.error(errMsg(e)));

  const canDecode = !busy && (pdf || images.length > 0 || text.trim().length >= 40);
  const busyLabel = pdf ? "Reading the PDF" : images.length ? "Reading the images" : "Reading your letter";
  const hasFiles = pdf || images.length > 0;

  return (
    <div
      className={`card fade-up ${over ? "!border-emerald-500 bg-emerald-500/5" : ""}`}
      style={{ transition: "border-color .2s, background-color .2s" }}
      onDragOver={(e) => { e.preventDefault(); setOver(true); }}
      onDragLeave={() => setOver(false)}
      onDrop={(e) => { e.preventDefault(); setOver(false); takeFiles([...e.dataTransfer.files]); }}
      data-testid="smart-input-panel"
    >
      <input
        ref={fileRef}
        type="file"
        hidden
        accept="application/pdf,.pdf,image/jpeg,image/png,image/webp"
        multiple
        onChange={(e) => { takeFiles([...e.target.files]); e.target.value = ""; }}
        data-testid="smart-input-file-input"
      />
      <div className="flex items-center justify-between gap-3">
        <label htmlFor="offer-text" className="font-display text-lg font-bold text-[var(--text)]">
          {country === "us" ? "Your US offer letter" : "Your offer letter"}
        </label>
        <button type="button" className="text-xs font-semibold text-[var(--accent-text)] hover:underline" onClick={sample} data-testid="sample-button">
          Try a sample
        </button>
      </div>

      {hasFiles ? (
        <div className="mt-4 space-y-2" data-testid="file-chips">
          {pdf && (
            <div className="flex items-center justify-between rounded-xl border border-[var(--line-2)] bg-[var(--field-bg)] px-4 py-3">
              <span className="flex items-center gap-3 text-sm font-semibold text-[var(--text-2)]"><FileUp size={16} className="text-[var(--accent-text)]" />{pdf.name}</span>
              <button type="button" aria-label="Remove PDF" onClick={clearFiles} className="text-[var(--text-faint)] hover:text-[var(--text)]" data-testid="remove-pdf"><X size={15} /></button>
            </div>
          )}
          {images.map((f, i) => (
            <div key={`${f.name}-${i}`} className="flex items-center justify-between rounded-xl border border-[var(--line-2)] bg-[var(--field-bg)] px-4 py-3">
              <span className="flex items-center gap-3 text-sm font-semibold text-[var(--text-2)]"><ImagePlus size={16} className="text-[var(--accent-text)]" />{f.name}</span>
              <button type="button" aria-label={`Remove ${f.name}`} onClick={() => setImages(images.filter((_, j) => j !== i))} className="text-[var(--text-faint)] hover:text-[var(--text)]" data-testid={`remove-image-${i}`}><X size={15} /></button>
            </div>
          ))}
          <p className="text-xs text-[var(--text-faint)]">
            {pdf ? "Scanned PDFs are fine - we read the pages visually." : `Up to 4 photos (${images.length}/4).`} Processed in memory, never stored.
          </p>
        </div>
      ) : (
        <textarea
          id="offer-text"
          rows={8}
          className="field mt-4 resize-y text-sm leading-relaxed"
          placeholder={country === "us"
            ? "Paste the offer letter here - or drop a PDF / photos anywhere on this card. Base salary, bonus, RSUs, signing bonus…"
            : "Paste the offer letter here - or drop a PDF / photos anywhere on this card. CTC, basic, bonus…"}
          value={text}
          onChange={(e) => onText(e.target.value)}
          data-testid="offer-text-input"
        />
      )}

      <div className="mt-4 flex flex-col sm:flex-row gap-3">
        <button type="button" className="btn-accent" disabled={!canDecode} onClick={decode} data-testid="decode-ai-button">
          <Sparkles size={16} /> Decode with AI
        </button>
        {!hasFiles && (
          <button type="button" className="btn-ghost" disabled={busy || !text.trim()} onClick={scan} data-testid="quick-scan-button">
            <ScanText size={16} /> Quick scan <span className="text-[10px] uppercase tracking-wider text-[var(--warn-strong)]">Beta</span>
          </button>
        )}
        <button type="button" className="btn-ghost" onClick={() => onQuickScan({})} data-testid="manual-entry-button">Type the numbers</button>
      </div>
      <p className="mt-3 text-xs text-[var(--text-faint)]">
        <button type="button" onClick={() => fileRef.current?.click()} className="font-semibold text-[var(--text-dim)] underline underline-offset-2 hover:text-[var(--accent-text)]" data-testid="browse-files-button">
          Choose a PDF or photos
        </button>{" "}
        or paste the letter. Quick scan runs offline (no AI) and pre-fills the form for you to verify.
      </p>

      {busy && <Scanning label={busyLabel} />}
      {notice && (
        <AiNotice message={notice.message}>
          {notice.pdfText && notice.pdfText.length > 20 && (
            <button type="button" className="btn-ghost !py-2 !px-4" onClick={scanPdfText} data-testid="pdf-quick-scan-button">Quick scan the PDF text</button>
          )}
          {!hasFiles && text.trim() && (
            <button type="button" className="btn-ghost !py-2 !px-4" onClick={scan} data-testid="notice-quick-scan-button">Quick scan instead</button>
          )}
          <button type="button" className="btn-ghost !py-2 !px-4" onClick={() => onQuickScan({})} data-testid="notice-manual-button">Enter manually</button>
        </AiNotice>
      )}
    </div>
  );
};
