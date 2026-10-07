import { lazy, Suspense } from "react";
import { BrowserRouter as Router, Routes, Route, Navigate } from "react-router-dom";
import { ProtectedRoute } from "./components/auth/ProtectedRoute";
import { Shell } from "./components/layout/Shell";
import Login from "./pages/Login";
import Unauthorized from "./pages/Unauthorized";

// Each page loads when it is first opened, so a compliance officer never downloads
// the engineer pages and the other way round.
const Dashboard = lazy(() => import("./pages/Dashboard"));
const RegulationUpload = lazy(() => import("./features/compliance-officer/pages/RegulationUpload"));
const ApprovalQueue = lazy(() => import("./features/compliance-officer/pages/ApprovalQueue"));
const Certificates = lazy(() => import("./features/compliance-officer/pages/Certificates"));
const PipelineMonitor = lazy(() => import("./features/ml-engineer/pages/PipelineMonitor"));
const ViolationReport = lazy(() => import("./features/ml-engineer/pages/ViolationReport"));
const ModelDiff = lazy(() => import("./features/ml-engineer/pages/ModelDiff"));
const ModelRegistry = lazy(() => import("./features/ml-engineer/pages/ModelRegistry"));

function PageLoading() {
  return (
    <p role="status" className="text-slate-300">
      Loading the page...
    </p>
  );
}

function App() {
  return (
    <Router>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route path="/unauthorized" element={<Unauthorized />} />
        
        <Route path="/" element={
          <ProtectedRoute>
            <Shell>
              <Suspense fallback={<PageLoading />}>
              <Dashboard />
              </Suspense>
            </Shell>
          </ProtectedRoute>
        } />

        <Route path="/regulations" element={
          <ProtectedRoute allowedRoles={['compliance_officer']}>
            <Shell>
              <Suspense fallback={<PageLoading />}>
              <RegulationUpload />
              </Suspense>
            </Shell>
          </ProtectedRoute>
        } />

        <Route path="/approval-queue" element={
          <ProtectedRoute allowedRoles={['compliance_officer']}>
            <Shell>
              <Suspense fallback={<PageLoading />}>
              <ApprovalQueue />
              </Suspense>
            </Shell>
          </ProtectedRoute>
        } />

        <Route path="/pipeline" element={
          <ProtectedRoute allowedRoles={['ml_engineer']}>
            <Shell>
              <Suspense fallback={<PageLoading />}>
              <PipelineMonitor />
              </Suspense>
            </Shell>
          </ProtectedRoute>
        } />

        <Route path="/violation-report" element={
          <ProtectedRoute allowedRoles={['ml_engineer']}>
            <Shell>
              <Suspense fallback={<PageLoading />}>
              <ViolationReport />
              </Suspense>
            </Shell>
          </ProtectedRoute>
        } />

        <Route path="/model-registry" element={
          <ProtectedRoute allowedRoles={['ml_engineer']}>
            <Shell>
              <Suspense fallback={<PageLoading />}>
              <ModelRegistry />
              </Suspense>
            </Shell>
          </ProtectedRoute>
        } />

        <Route path="/model-diff" element={
          <ProtectedRoute allowedRoles={['ml_engineer']}>
            <Shell>
              <Suspense fallback={<PageLoading />}>
              <ModelDiff />
              </Suspense>
            </Shell>
          </ProtectedRoute>
        } />

        <Route path="/certificates" element={
          <ProtectedRoute allowedRoles={['compliance_officer']}>
            <Shell>
              <Suspense fallback={<PageLoading />}>
              <Certificates />
              </Suspense>
            </Shell>
          </ProtectedRoute>
        } />

        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Router>
  );
}

export default App;
