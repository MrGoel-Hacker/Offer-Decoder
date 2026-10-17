import { Link } from "react-router-dom";

export const LogoMark = ({ size = 28 }) => (
  <svg width={size} height={size} viewBox="0 0 32 32" aria-hidden="true">
    <rect x="1" y="1" width="30" height="30" rx="9" fill="#0f1522" stroke="#10B981" strokeWidth="1.5" />
    <path d="M9 11h14M9 16h9M9 21h5" stroke="#334155" strokeWidth="2.2" strokeLinecap="round" />
    <path d="M17 21.5l2.6 2.6L25 18" stroke="#10B981" strokeWidth="2.4" fill="none" strokeLinecap="round" strokeLinejoin="round" />
  </svg>
);

export const Header = () => (
  <header className="sticky top-0 z-40 border-b border-[#1c2536] bg-[#090d16]/80 backdrop-blur-xl grain">
    <div className="max-w-3xl mx-auto flex items-center justify-between px-5 py-3.5">
      <Link to="/" className="flex items-center gap-2.5" data-testid="brand-home-link">
        <LogoMark />
        <span className="font-display text-lg font-extrabold tracking-tight text-slate-50">
          Offer<span className="text-emerald-400">Decode</span>
        </span>
      </Link>
      <span className="rounded-full border border-slate-700 px-3 py-1 text-[11px] font-semibold text-slate-400" data-testid="regime-badge">
        India · FY 2026-27
      </span>
    </div>
  </header>
);
