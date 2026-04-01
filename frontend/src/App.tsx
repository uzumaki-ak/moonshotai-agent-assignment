// this file defines app routes and layout
import { Navigate, Route, Routes } from "react-router-dom";

import { PageShell } from "./components/layout/PageShell";
import { BrandPage } from "./pages/BrandPage";
import { ChatPage } from "./pages/ChatPage";
import { ComparePage } from "./pages/ComparePage";
import { InsightsPage } from "./pages/InsightsPage";
import { NotFoundPage } from "./pages/NotFoundPage";
import { OverviewPage } from "./pages/OverviewPage";
import { PipelinePage } from "./pages/PipelinePage";
import { ProductPage } from "./pages/ProductPage";

export default function App() {
  // this component maps url paths to route pages
  return (
    <PageShell>
      <Routes>
        <Route path="/" element={<OverviewPage />} />
        <Route path="/compare" element={<ComparePage />} />
        <Route path="/chat" element={<ChatPage />} />
        <Route path="/brands/:brandId" element={<BrandPage />} />
        <Route path="/products/:productId" element={<ProductPage />} />
        <Route path="/insights" element={<InsightsPage />} />
        <Route path="/pipeline" element={<PipelinePage />} />
        <Route path="/home" element={<Navigate to="/" replace />} />
        <Route path="*" element={<NotFoundPage />} />
      </Routes>
    </PageShell>
  );
}
