import { BrowserRouter as Router, Routes, Route, Navigate } from "react-router-dom";
import { ProtectedRoute } from "./components/auth/ProtectedRoute";
import { Shell } from "./components/layout/Shell";
import Login from "./pages/Login";
import Dashboard from "./pages/Dashboard";
import Unauthorized from "./pages/Unauthorized";
import RegulationUpload from "./features/compliance-officer/pages/RegulationUpload";
import ApprovalQueue from "./features/compliance-officer/pages/ApprovalQueue";
import PipelineMonitor from "./features/ml-engineer/pages/PipelineMonitor";
import ViolationReport from "./features/ml-engineer/pages/ViolationReport";
import ModelDiff from "./features/ml-engineer/pages/ModelDiff";
import ModelRegistry from "./features/ml-engineer/pages/ModelRegistry";
import Certificates from "./features/compliance-officer/pages/Certificates";

function App() {
  return (
    <Router>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route path="/unauthorized" element={<Unauthorized />} />
        
        <Route path="/" element={
          <ProtectedRoute>
            <Shell>
              <Dashboard />
            </Shell>
          </ProtectedRoute>
        } />

        <Route path="/regulations" element={
          <ProtectedRoute allowedRoles={['compliance_officer']}>
            <Shell>
              <RegulationUpload />
            </Shell>
          </ProtectedRoute>
        } />

        <Route path="/approval-queue" element={
          <ProtectedRoute allowedRoles={['compliance_officer']}>
            <Shell>
              <ApprovalQueue />
            </Shell>
          </ProtectedRoute>
        } />

        <Route path="/pipeline" element={
          <ProtectedRoute allowedRoles={['ml_engineer']}>
            <Shell>
              <PipelineMonitor />
            </Shell>
          </ProtectedRoute>
        } />

        <Route path="/violation-report" element={
          <ProtectedRoute allowedRoles={['ml_engineer']}>
            <Shell>
              <ViolationReport />
            </Shell>
          </ProtectedRoute>
        } />

        <Route path="/model-registry" element={
          <ProtectedRoute allowedRoles={['ml_engineer']}>
            <Shell>
              <ModelRegistry />
            </Shell>
          </ProtectedRoute>
        } />

        <Route path="/model-diff" element={
          <ProtectedRoute allowedRoles={['ml_engineer']}>
            <Shell>
              <ModelDiff />
            </Shell>
          </ProtectedRoute>
        } />

        <Route path="/certificates" element={
          <ProtectedRoute allowedRoles={['compliance_officer']}>
            <Shell>
              <Certificates />
            </Shell>
          </ProtectedRoute>
        } />

        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Router>
  );
}

export default App;
