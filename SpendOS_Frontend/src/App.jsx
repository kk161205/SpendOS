import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider } from './context/AuthContext';
import { SessionProvider } from './context/SessionContext';
import ProtectedRoute from './components/Auth/ProtectedRoute';

// Lazy load views or import them directly. 
// For now, importing placeholders that will be implemented soon.
import LoginPage from './components/Auth/LoginPage';
import RegisterPage from './components/Auth/RegisterPage';
import DashboardLayout from './components/Dashboard/DashboardLayout';
import SessionList from './components/Dashboard/SessionList';
import ProcurementForm from './components/ProcurementForm/ProcurementForm';
import ResultsPage from './components/Results/ResultsPage';

import { useEffect } from 'react';

function App() {
  useEffect(() => {
    const handleAuthExpired = () => {
      // Clear local storage and redirect
      localStorage.removeItem('csrf_token');
      window.location.href = '/login?expired=true';
    };
    window.addEventListener('auth:expired', handleAuthExpired);
    return () => window.removeEventListener('auth:expired', handleAuthExpired);
  }, []);

  return (
    <AuthProvider>
      <SessionProvider>
        <Router>
          <Routes>
            {/* Public Routes */}
            <Route path="/login" element={<LoginPage />} />
            <Route path="/register" element={<RegisterPage />} />

            {/* Protected Routes */}
            <Route path="/dashboard" element={
              <ProtectedRoute>
                <DashboardLayout />
              </ProtectedRoute>
            }>
              <Route index element={<SessionList />} />
              <Route path="new" element={<ProcurementForm />} />
              <Route path="results" element={<ResultsPage />} />
            </Route>

            {/* Fallback */}
            <Route path="*" element={<Navigate to="/dashboard" replace />} />
          </Routes>
        </Router>
      </SessionProvider>
    </AuthProvider>
  );
}

export default App;
