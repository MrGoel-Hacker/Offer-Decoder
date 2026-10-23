import { useEffect } from "react";
import "@/App.css";
import { BrowserRouter, Routes, Route, Link } from "react-router-dom";
import { Toaster } from "sonner";
import Home from "@/pages/Home";
import SharedReport from "@/pages/SharedReport";
import MyReports from "@/pages/MyReports";
import Privacy from "@/pages/Privacy";
import { Header } from "@/components/Header";
import { AuthProvider } from "@/lib/auth";
import { applyTheme, getTheme, useTheme } from "@/lib/theme";

function App() {
  const theme = useTheme();
  useEffect(() => {
    applyTheme(getTheme());
  }, []);
  return (
    <div className="App min-h-screen">
      <BrowserRouter>
        <AuthProvider>
        <Header />
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/r/:id" element={<SharedReport />} />
          <Route path="/privacy" element={<Privacy />} />
          <Route path="/my/reports" element={<MyReports />} />
        </Routes>
        <footer className="max-w-3xl mx-auto px-5 py-12 text-xs text-[var(--text-faint)]" data-testid="site-footer">
          India: new regime, FY 2026-27 · US: tax year 2026, single filer. Estimates only - not tax advice. No login to decode; sign in only if you save a report.{" "}
          <Link to="/privacy" className="text-[var(--text-dim)] underline underline-offset-2 hover:text-[var(--accent-text)]" data-testid="footer-privacy-link">Privacy</Link>
        </footer>
      </AuthProvider>
      </BrowserRouter>
      <Toaster theme={theme} position="top-center" richColors />
    </div>
  );
}

export default App;
