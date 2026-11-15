import { useEffect } from "react";
import "@/App.css";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import { Toaster } from "sonner";
import Home from "@/pages/Home";
import SharedReport from "@/pages/SharedReport";
import MyReports from "@/pages/MyReports";
import Privacy from "@/pages/Privacy";
import PurchasedReport from "@/pages/PurchasedReport";
import SavedPurchasedReport from "@/pages/SavedPurchasedReport";
import SelectRegion from "@/pages/SelectRegion";
import { RegionFooter, RegionMetadata } from "@/components/RegionLayout";
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
        <RegionMetadata />
        <Header />
        <Routes>
          <Route path="/" element={<SelectRegion />} />
          <Route path="/india" element={<Home key="india" country="in" />} />
          <Route path="/usa" element={<Home key="usa" country="us" />} />
          <Route path="/r/:id" element={<SharedReport />} />
          <Route path="/privacy" element={<Privacy />} />
          <Route path="/my/reports" element={<MyReports />} />
          <Route path="/checkout/:token" element={<PurchasedReport />} />
          <Route path="/paid-report/:id" element={<SavedPurchasedReport />} />
        </Routes>
        <RegionFooter />
      </AuthProvider>
      </BrowserRouter>
      <Toaster theme={theme} position="top-center" richColors />
    </div>
  );
}

export default App;
