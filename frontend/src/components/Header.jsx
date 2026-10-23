import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { LogOut, Moon, Sun, UserRound } from "lucide-react";
import { setTheme, useTheme } from "@/lib/theme";
import { useAuth } from "@/lib/auth";
import { AuthModal } from "@/components/AuthModal";

const UserMenu = () => {
  const { user, logout } = useAuth();
  const [open, setOpen] = useState(false);
  const ref = useRef(null);

  useEffect(() => {
    const onDoc = (e) => { if (ref.current && !ref.current.contains(e.target)) setOpen(false); };
    document.addEventListener("mousedown", onDoc);
    return () => document.removeEventListener("mousedown", onDoc);
  }, []);

  return (
    <div className="relative" ref={ref}>
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        className="flex h-8 items-center gap-2 rounded-full border border-[var(--line-2)] pl-1 pr-3 text-xs font-semibold text-[var(--text)] hover:border-emerald-500/60"
        data-testid="user-menu-button"
      >
        {user.picture ? (
          <img src={user.picture} alt="" className="h-6 w-6 rounded-full" referrerPolicy="no-referrer" />
        ) : (
          <span className="flex h-6 w-6 items-center justify-center rounded-full bg-emerald-500/15"><UserRound size={13} /></span>
        )}
        <span className="max-w-[110px] truncate">{user.name.split(" ")[0]}</span>
      </button>
      {open && (
        <div className="absolute right-0 mt-2 w-44 rounded-xl border border-[var(--line)] bg-[var(--bg)] p-1.5 shadow-xl" data-testid="user-menu">
          <Link
            to="/my/reports"
            onClick={() => setOpen(false)}
            className="block rounded-lg px-3 py-2 text-sm text-[var(--text)] hover:bg-emerald-500/10"
            data-testid="my-reports-link"
          >
            My reports
          </Link>
          <button
            type="button"
            onClick={() => { setOpen(false); logout(); }}
            className="flex w-full items-center gap-2 rounded-lg px-3 py-2 text-left text-sm text-[var(--text-dim)] hover:bg-emerald-500/10 hover:text-[var(--text)]"
            data-testid="sign-out-button"
          >
            <LogOut size={14} /> Sign out
          </button>
        </div>
      )}
    </div>
  );
};

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
  const { user, ready } = useAuth();
  const [showAuth, setShowAuth] = useState(false);
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
          {ready && (user ? (
            <UserMenu />
          ) : (
            <button
              type="button"
              onClick={() => setShowAuth(true)}
              className="rounded-full border border-[var(--line-2)] px-3.5 py-1.5 text-xs font-semibold text-[var(--text)] hover:border-emerald-500/60 hover:text-[var(--accent-text)]"
              data-testid="header-sign-in"
            >
              Sign in
            </button>
          ))}
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
      <AuthModal open={showAuth} onClose={() => setShowAuth(false)} title="Sign in" />
    </header>
  );
};
