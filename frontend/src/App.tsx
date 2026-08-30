import { Navigate, Route, Routes } from 'react-router-dom';
import { DashboardLayout } from './layouts/DashboardLayout';
import { Login } from './pages/Login';
import { Dashboard } from './pages/Dashboard';
import { Heatmap } from './pages/Heatmap';
import { Alerts } from './pages/Alerts';
import { PredictionDetail } from './pages/PredictionDetail';
import { Investigation } from './pages/Investigation';
import { Settings } from './pages/Settings';
import { authService } from './services/services';

import InvestigationWorkspace from './components/InvestigationWorkspace';

function RequireAuth({ children }: { children: React.ReactNode }) {
  if (!authService.current()) {
    return <Navigate to="/login" replace />;
  }
  return <>{children}</>;
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route
        path="/"
        element={
          <RequireAuth>
            <DashboardLayout />
          </RequireAuth>
        }
      >
        <Route index element={<Navigate to="/dashboard" replace />} />
        <Route path="dashboard" element={<Dashboard />} />
        <Route path="heatmap" element={<Heatmap />} />
        <Route path="alerts" element={<Alerts />} />
        <Route path="predictions/:id" element={<PredictionDetail />} />
        <Route path="investigations/:id" element={<Investigation />} />
        <Route path="investigations/:id/graph" element={<InvestigationWorkspace />} />
        <Route path="graph" element={<InvestigationWorkspace />} />
        <Route path="settings" element={<Settings />} />
      </Route>
      <Route path="*" element={<Navigate to="/dashboard" replace />} />
    </Routes>
  );
}