import React from 'react';
import { useAuth } from '@/lib/auth/useAuth';
import CODashboard from '@/features/compliance-officer/pages/Dashboard';
import MLEDashboard from '@/features/ml-engineer/pages/Dashboard';

/** Same system, two interfaces: each role gets its own dashboard. */
const Dashboard: React.FC = () => {
  const { role } = useAuth();
  return role === 'ml_engineer' ? <MLEDashboard /> : <CODashboard />;
};

export default Dashboard;
