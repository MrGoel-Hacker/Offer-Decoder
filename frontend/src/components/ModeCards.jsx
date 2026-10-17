import { ClipboardType, FileText, Images, SlidersHorizontal } from "lucide-react";

export const MODES = [
  { id: "paste", icon: ClipboardType, title: "Paste the letter", desc: "Copy the text from email or a doc." },
  { id: "pdf", icon: FileText, title: "Upload a PDF", desc: "We read the text on our server." },
  { id: "image", icon: Images, title: "Photos / screenshots", desc: "Up to 4 images of the letter." },
  { id: "manual", icon: SlidersHorizontal, title: "Type the numbers", desc: "CTC, basic, bonus - no AI used." },
];

export const ModeCards = ({ active, onPick }) => (
  <div className="grid grid-cols-2 gap-3 sm:gap-4" data-testid="mode-cards">
    {MODES.map((m, i) => {
      const on = active === m.id;
      const Icon = m.icon;
      return (
        <button
          key={m.id}
          type="button"
          onClick={() => onPick(m.id)}
          data-testid={`input-mode-${m.id}-card`}
          style={{ animationDelay: `${120 + i * 70}ms` }}
          className={`fade-up group text-left rounded-2xl border p-4 sm:p-5 ${
            on ? "border-emerald-500/70 bg-emerald-500/[0.07]" : "border-[#1c2536] bg-[#0f1522]/80 hover:border-slate-600"
          }`}
        >
          <span className={`mb-4 inline-flex h-10 w-10 items-center justify-center rounded-xl border ${on ? "border-emerald-500/50 text-emerald-400" : "border-slate-700 text-slate-400 group-hover:text-emerald-400"}`} style={{ transition: "color .2s" }}>
            <Icon size={18} />
          </span>
          <span className="block font-display text-[15px] sm:text-base font-bold text-slate-100">{m.title}</span>
          <span className="mt-1 block text-xs sm:text-sm text-slate-400">{m.desc}</span>
        </button>
      );
    })}
  </div>
);
