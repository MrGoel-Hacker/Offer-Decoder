import { createContext, useCallback, useContext, useEffect, useRef, useState } from "react";
import { http } from "@/lib/api";

// The Google OAuth client ID is public by design (it is embedded in the page by
// Google's own sign-in library). Placeholder until the OAuth client is created.
export const GOOGLE_CLIENT_ID = "983915537425-bvtsnlntosva6t7phijp4u97pt5broru.apps.googleusercontent.com";
export const AUTH_READY = !GOOGLE_CLIENT_ID.startsWith("PENDING");

const TOKEN_KEY = "od_token";
const AuthCtx = createContext(null);

export const useAuth = () => useContext(AuthCtx);

let gsiPromise = null;
const loadGsi = () => {
  if (!gsiPromise) {
    gsiPromise = new Promise((resolve, reject) => {
      const s = document.createElement("script");
      s.src = "https://accounts.google.com/gsi/client";
      s.async = true;
      s.onload = resolve;
      s.onerror = () => reject(new Error("Could not load Google sign-in."));
      document.head.appendChild(s);
    });
  }
  return gsiPromise;
};

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    const token = localStorage.getItem(TOKEN_KEY);
    if (!token) {
      setReady(true);
      return;
    }
    http.get("/auth/me", { headers: { authorization: `Bearer ${token}` } })
      .then(({ data }) => setUser(data))
      .catch(() => localStorage.removeItem(TOKEN_KEY))
      .finally(() => setReady(true));
  }, []);

  const login = useCallback(async (credential) => {
    const { data } = await http.post("/auth/google", { credential });
    localStorage.setItem(TOKEN_KEY, data.token);
    setUser(data.user);
    return data.user;
  }, []);

  const logout = useCallback(async () => {
    const token = localStorage.getItem(TOKEN_KEY);
    localStorage.removeItem(TOKEN_KEY);
    setUser(null);
    if (token) {
      try { await http.post("/auth/logout", {}, { headers: { authorization: `Bearer ${token}` } }); } catch { /* session expiry is harmless */ }
    }
  }, []);

  const authHeaders = useCallback(() => {
    const token = localStorage.getItem(TOKEN_KEY);
    return token ? { authorization: `Bearer ${token}` } : {};
  }, []);

  return <AuthCtx.Provider value={{ user, ready, login, logout, authHeaders }}>{children}</AuthCtx.Provider>;
};

export const GoogleButton = ({ onCredential, onError }) => {
  const ref = useRef(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    let cancelled = false;
    if (!AUTH_READY) return;
    loadGsi()
      .then(() => {
        if (cancelled || !ref.current || !window.google) return;
        window.google.accounts.id.initialize({
          client_id: GOOGLE_CLIENT_ID,
          callback: (resp) => resp.credential && onCredential(resp.credential),
        });
        window.google.accounts.id.renderButton(ref.current, { theme: "outline", size: "large", width: 260, text: "continue_with" });
      })
      .catch(() => { if (!cancelled) { setFailed(true); onError && onError(); } });
    return () => { cancelled = true; };
  }, [onCredential, onError]);

  if (!AUTH_READY) {
    return <p className="text-sm text-[var(--text-dim)]">Sign-in is being set up - check back soon.</p>;
  }
  if (failed) {
    return <p className="text-sm text-[var(--text-dim)]">Google sign-in could not load. Check your connection and try again.</p>;
  }
  return <div ref={ref} data-testid="google-signin-button" />;
};
