import { useEffect, useState } from "react";
import { ImagePlus, Sparkles, X } from "lucide-react";
import { toast } from "sonner";
import { http, errMsg } from "@/lib/api";
import { AiNotice, Scanning } from "@/components/AiNotice";
import { aiToSession } from "@/components/PasteMode";
import { DropZone } from "@/components/PdfMode";

const OK = ["image/jpeg", "image/png", "image/webp"];

export const ImageMode = ({ onDecoded, onQuickScan }) => {
  const [files, setFiles] = useState([]);
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState("");
  const [previews, setPreviews] = useState([]);

  useEffect(() => {
    const urls = files.map((f) => URL.createObjectURL(f));
    setPreviews(urls);
    return () => urls.forEach((u) => URL.revokeObjectURL(u));
  }, [files]);

  const add = (list) => {
    const good = list.filter((f) => OK.includes(f.type) && f.size <= 5 * 1024 * 1024);
    if (good.length < list.length) toast.warning("Only JPG/PNG/WEBP under 5 MB each.");
    setFiles((prev) => [...prev, ...good].slice(0, 4));
    setNotice("");
  };

  const submit = async () => {
    setBusy(true);
    setNotice("");
    try {
      const fd = new FormData();
      files.forEach((f) => fd.append("files", f));
      const { data } = await http.post("/extract/images", fd);
      if (data.ok) onDecoded(aiToSession(data, "ai"));
      else setNotice(data.message);
    } catch (e) {
      toast.error(errMsg(e));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="card fade-up" data-testid="image-mode-panel">
      <h2 className="font-display text-lg font-bold text-slate-100">Photos or screenshots of the letter</h2>
      <DropZone accept="image/jpeg,image/png,image/webp" multiple onFiles={add} testId="image-dropzone">
        <ImagePlus className="text-emerald-400" />
        <p className="mt-3 text-sm font-semibold text-slate-200">Tap to add pages ({files.length}/4)</p>
        <p className="mt-1 text-xs text-slate-500">Sent straight to the vision model, not stored.</p>
      </DropZone>
      {files.length > 0 && (
        <div className="mt-4 grid grid-cols-4 gap-2" data-testid="image-previews">
          {previews.map((u, i) => (
            <div key={u} className="relative aspect-[3/4] overflow-hidden rounded-lg border border-slate-700">
              <img src={u} alt={`Page ${i + 1}`} className="h-full w-full object-cover" />
              <button type="button" aria-label="Remove image" onClick={() => setFiles(files.filter((_, j) => j !== i))} className="absolute right-1 top-1 rounded-full bg-black/70 p-1 text-slate-200" data-testid={`image-remove-${i}`}>
                <X size={12} />
              </button>
            </div>
          ))}
        </div>
      )}
      <button type="button" className="btn-accent mt-4 w-full sm:w-auto" disabled={!files.length || busy} onClick={submit} data-testid="image-decode-button">
        <Sparkles size={16} /> Decode images
      </button>
      {busy && <Scanning label="Reading the images" />}
      {notice && (
        <AiNotice message={notice}>
          <p className="w-full text-xs text-amber-200/80">Quick scan needs text - use "Paste the letter" above, or type the numbers here.</p>
          <button type="button" className="btn-ghost !py-2 !px-4" onClick={() => onQuickScan({})} data-testid="image-manual-button">Enter manually</button>
        </AiNotice>
      )}
    </div>
  );
};
