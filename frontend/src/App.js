import { useEffect } from "react";
import "@/App.css";
import { BrowserRouter, Routes, Route, Link } from "react-router-dom";
import { Toaster } from "sonner";
import Home from "@/pages/Home";
import SharedReport from "@/pages/SharedReport";
import Privacy from "@/pages/Privacy";
import { Header } from "@/components/Header";

function App() {
  useEffect(() => {
    document.documentElement.classList.add("dark");
  }, []);
  return (
    <div className="App min-h-screen">
      <BrowserRouter>
        <Header />
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/r/:id" element={<SharedReport />} />
          <Route path="/privacy" element={<Privacy />} />
        </Routes>
        <footer className="max-w-3xl mx-auto px-5 py-12 text-xs text-slate-500" data-testid="site-footer">
          New tax regime, FY 2026-27. Estimates only - not tax advice. No login, nothing stored unless you save a report.{" "}
          <Link to="/privacy" className="text-slate-400 underline underline-offset-2 hover:text-emerald-400" data-testid="footer-privacy-link">Privacy</Link>
        </footer>
      </BrowserRouter>
      <Toaster theme="dark" position="top-center" richColors />
    </div>
  );
}

export default App;
