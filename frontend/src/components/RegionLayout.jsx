import { useEffect } from "react";
import { Link, useLocation } from "react-router-dom";
import { regionFromPath } from "@/lib/region";

export function RegionMetadata() {
  const { pathname } = useLocation();
  useEffect(() => {
    const country = regionFromPath(pathname);
    const title = country === "us" ? "OfferDecoder USA - take-home pay, taxes and offer reports" : country === "in" ? "OfferDecoder India - in-hand salary, CTC and offer reports" : "OfferDecoder - understand your job offer";
    const description = country === "us" ? "Decode your US job offer: take-home pay, bonus, RSUs, tax estimates and offer flags. Sign in with Google and unlock a downloadable report." : country === "in" ? "Decode your Indian job offer: monthly in-hand salary, CTC, PF, gratuity, tax estimates and offer flags. Sign in with Google and unlock a downloadable report." : "Choose your region to decode your job offer, understand take-home salary and unlock your full downloadable report.";
    document.title = title;
    for (const [selector, content] of [['meta[name="description"]', description], ['meta[property="og:title"]', title], ['meta[property="og:description"]', description], ['meta[property="og:url"]', `${window.location.origin}${pathname}`]]) {
      document.querySelector(selector)?.setAttribute("content", content);
    }
    document.querySelector('link[rel="canonical"]')?.setAttribute("href", `${window.location.origin}${pathname}`);
  }, [pathname]);
  return null;
}

export function RegionFooter() {
  const country = regionFromPath(useLocation().pathname);
  return <footer className="max-w-3xl mx-auto px-5 py-12 text-xs text-[var(--text-faint)]" data-testid="site-footer">
    {country === "us" ? "US: tax year 2026, single filer. " : country === "in" ? "India: new regime, FY 2026-27. " : ""}Estimates only - not tax advice. Purchased and saved reports are stored for up to 90 days.{" "}
    <Link to="/privacy" className="text-[var(--text-dim)] underline underline-offset-2" data-testid="footer-privacy-link">Privacy</Link>
    {country && <Link to="/" className="ml-4 text-[var(--text-dim)] underline underline-offset-2">Change region</Link>}
  </footer>;
}
