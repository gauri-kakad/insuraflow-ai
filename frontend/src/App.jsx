import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider, useAuth } from './context/AuthContext';
import DashboardLayout from './layouts/DashboardLayout';
import LoginPage from './pages/LoginPage';
import DashboardPage from './pages/DashboardPage';
import ClaimSubmissionPage from './pages/ClaimSubmissionPage';
import ProcessingCenterPage from './pages/ProcessingCenterPage';
import ClaimAnalysisPage from './pages/ClaimAnalysisPage';
import HumanReviewPage from './pages/HumanReviewPage';
import ClaimHistoryPage from './pages/ClaimHistoryPage';
import ReportsAnalyticsPage from './pages/ReportsAnalyticsPage';

function ProtectedRoute({ children }) {
  const { user, loading } = useAuth();
  if (loading) {
    return <div className="min-h-screen flex items-center justify-center text-sm text-slate-500">Loading workspace...</div>;
  }
  if (!user) {
    return <Navigate to="/login" replace />;
  }
  return children;
}

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route
            path="/"
            element={
              <ProtectedRoute>
                <DashboardLayout />
              </ProtectedRoute>
            }
          >
            <Route index element={<Navigate to="/dashboard" replace />} />
            <Route path="dashboard" element={<DashboardPage />} />
            <Route path="submit" element={<ClaimSubmissionPage />} />
            <Route path="processing" element={<ProcessingCenterPage />} />
            <Route path="analysis" element={<ClaimAnalysisPage />} />
            <Route path="review" element={<HumanReviewPage />} />
            <Route path="history" element={<ClaimHistoryPage />} />
            <Route path="reports" element={<ReportsAnalyticsPage />} />
          </Route>
          <Route path="*" element={<Navigate to="/dashboard" replace />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
}
