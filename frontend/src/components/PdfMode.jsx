import { useRef, useState } from "react";
import { FileUp, Sparkles } from "lucide-react";
import { toast } from "sonner";
import { http, errMsg } from "@/lib/api";
import { AiNotice, Scanning } from "@/components/AiNotice";
import { aiToSession, runQuickScan } from "@/components/PasteMode";

export const DropZone = ({ accept, multiple, onFiles, testId, children }) => {
  const ref = useRef(null);
  const [over, setOver] = useState(false);
  return (
    <div
      role="button"
      tabIndex={0}
      onClick={() => ref.current?.click()}
      onKeyDown={(e) => e.key === "Enter" && ref.current?.click()}
      onDragOver={(e) => { e.preventDefault(); setOver(true); }}
      onDragLeave={() => setOver(false)}
      onDrop={(e) => { e.preventDefault(); setOver(false); onFiles([...e.dataTransfer.files]); }}
      className={`mt-4 flex cursor-pointer flex-col items-center justify-center rounded-2xl border-2 border-dashed px-5 py-10 text-center ${over ? "border-emerald-500 bg-emerald-500/5" : "border-slate-700 hover:border-slate-500"}`}
      style={{ transition: "border-color .2s, background-color .2s" }}
      data-testid={testId}
    >
      <input ref={ref} type="file" hidden accept={accept} multiple={multiple} onChange={(e) => { onFiles([...e.target.files]); e.target.value = ""; }} data-testid={`${testId}-input`} />
      {children}
    </div>
  );
};

export const PdfMode = ({ onDecoded, onQuickScan }) => {
  const [file, setFile] = useState(null);
  const [busy, setBusy] = useState(false);
  const [res, setRes] = useState(null);

  const pick = (files) => {
    const f = files.find((x) => x.type === "application/pdf" || x.name.toLowerCase().endsWith(".pdf"));
    if (!f) return toast.error("Choose a PDF file.");
    if (f.size > 10 * 1024 * 1024) return toast.error("PDF is larger than 10 MB.");
    setFile(f);
    setRes(null);
  };

  const submit = async () => {
    setBusy(true);
    setRes(null);
    try {
      const fd = new FormData();
      fd.append("file", file);
      const { data } = await http.post("/extract/pdf", fd);
      if (data.ok) onDecoded(aiToSession(data, "ai"));
      else setRes(data);
    } catch (e) {
      toast.error(errMsg(e));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="card fade-up" data-testid="pdf-mode-panel">
      <h2 className="font-display text-lg font-bold text-slate-100">Upload the offer letter PDF</h2>
      <DropZone accept="application/pdf,.pdf" onFiles={pick} testId="pdf-dropzone">
        <FileUp className="text-emerald-400" />
        <p className="mt-3 text-sm font-semibold text-slate-200">{file ? file.name : "Tap to choose or drop a PDF"}</p>
        <p className="mt-1 text-xs text-slate-500">Up to 10 MB. Text is extracted on our server, the file isn't stored.</p>
      </DropZone>
      <button type="button" className="btn-accent mt-4 w-full sm:w-auto" disabled={!file || busy} onClick={submit} data-testid="pdf-decode-button">
        <Sparkles size={16} /> Decode PDF
      </button>
      {busy && <Scanning label="Extracting and reading" />}
      {res && (
        <AiNotice message={res.message}>
          {res.text && res.text.length > 20 && (
            <button type="button" className="btn-ghost !py-2 !px-4" onClick={() => runQuickScan(res.text, onQuickScan).catch((e) => toast.error(errMsg(e)))} data-testid="pdf-quick-scan-button">
              Quick scan the PDF text
            </button>
          )}
          <button type="button" className="btn-ghost !py-2 !px-4" onClick={() => onQuickScan({})} data-testid="pdf-manual-button">Enter manually</button>
        </AiNotice>
      )}
    </div>
  );
};
