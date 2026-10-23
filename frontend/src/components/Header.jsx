import { Link } from "react-router-dom";
import { Moon, Sun } from "lucide-react";
import { setTheme, useTheme } from "@/lib/theme";

export const LogoMark = ({ size = 28 }) => (
  <svg width={size} height={size} viewBox="0 0 32 32" aria-hidden="true">
    <rect x="1" y="1" width="30" height="30" rx="9" fill="#0f1522" stroke="#10B981" strokeWidth="1.5" />
    <path d="M9 11h14M9 16h9M9 21h5" stroke="#334155" strokeWidth="2.2" strokeLinecap="round" />
    <path d="M17 21.5l2.6 2.6L25 18" stroke="#10B981" strokeWidth="2.4" fill="none" strokeLinecap="round" strokeLinejoin="round" />
  </svg>
);

export const Header = () => {
  const theme = useTheme();
  const toggle = () => setTheme(theme === "light" ? "dark" : "light");
  return (
    <header className="sticky top-0 z-40 border-b border-[var(--line)] bg-[color-mix(in_srgb,var(--bg)_82%,transparent)] backdrop-blur-xl grain">
      <div className="max-w-3xl mx-auto flex items-center justify-between px-5 py-3.5">
        <Link to="/" className="flex items-center gap-2.5" data-testid="brand-home-link">
          <LogoMark />
          <span className="font-display text-lg font-extrabold tracking-tight text-[var(--text)]">
            Offer<span className="text-[var(--accent-text)]">Decode</span>
          </span>
        </Link>
        <div className="flex items-center gap-2.5">
          <span className="rounded-full border border-[var(--line-2)] px-3 py-1 text-[11px] font-semibold text-[var(--text-dim)]" data-testid="regime-badge">
            India + US · 2026
          </span>
          <button
            type="button"
            onClick={toggle}
            aria-label={theme === "light" ? "Switch to dark mode" : "Switch to light mode"}
            className="flex h-8 w-8 items-center justify-center rounded-full border border-[var(--line-2)] text-[var(--text-dim)] hover:border-emerald-500/60 hover:text-[var(--accent-text)]"
            style={{ transition: "border-color .2s, color .2s" }}
            data-testid="theme-toggle"
          >
            {theme === "light" ? <Moon size={15} /> : <Sun size={15} />}
          </button>
        </div>
      </div>
    </header>
  );
};
