import { BrowserRouter as Router, Routes, Route, Navigate } from "react-router-dom";
import { ProtectedRoute } from "./components/auth/ProtectedRoute";
import { Shell } from "./components/layout/Shell";
import Login from "./pages/Login";
import Dashboard from "./pages/Dashboard";
import Unauthorized from "./pages/Unauthorized";
import Regulations from "./features/compliance-officer/pages/Regulations";
import Pipeline from "./features/ml-engineer/pages/Pipeline";

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
              <Regulations />
            </Shell>
          </ProtectedRoute>
        } />

        <Route path="/pipeline" element={
          <ProtectedRoute allowedRoles={['ml_engineer']}>
            <Shell>
              <Pipeline />
            </Shell>
          </ProtectedRoute>
        } />

        <Route path="/certificates" element={
          <ProtectedRoute>
            <Shell>
              <div className="p-12 text-center text-slate-500 italic">
                Certificate Registry coming soon...
              </div>
            </Shell>
          </ProtectedRoute>
        } />

        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Router>
  );
}

export default App;
