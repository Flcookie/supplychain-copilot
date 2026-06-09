import { BrowserRouter, Navigate, Route, Routes, useParams } from "react-router-dom";
import { CopilotProvider } from "./context/CopilotContext";
import { AppShell } from "./components/layout/AppShell";
import { ErrorBoundary } from "./components/shared/ErrorBoundary";
import { HomePage } from "./pages/HomePage";
import { QualificationPage } from "./pages/QualificationPage";
import { PolicyPage } from "./pages/PolicyPage";
import { ReviewQueuePage } from "./pages/ReviewQueuePage";
import { SupplierDetailPage, SuppliersPage } from "./pages/SuppliersPage";

function SupplierDetailRoute() {
  const { id } = useParams();
  if (!id) return <Navigate to="/suppliers" replace />;
  return <SupplierDetailPage supplierId={id} />;
}

export default function App() {
  return (
    <ErrorBoundary>
      <CopilotProvider>
        <BrowserRouter>
          <Routes>
            <Route element={<AppShell />}>
              <Route index element={<HomePage />} />
              <Route path="suppliers" element={<SuppliersPage />} />
              <Route path="suppliers/:id" element={<SupplierDetailRoute />} />
              <Route path="qualification" element={<QualificationPage />} />
              <Route path="review" element={<ReviewQueuePage />} />
              <Route path="policy" element={<PolicyPage />} />
            </Route>
          </Routes>
        </BrowserRouter>
      </CopilotProvider>
    </ErrorBoundary>
  );
}
