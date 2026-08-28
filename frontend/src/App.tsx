import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider, useAuth } from './hooks/useAuth';
import Nav from './components/Nav';
import LoginPage from './pages/LoginPage';
import CatalogPage from './pages/CatalogPage';
import SessionDetailPage from './pages/SessionDetailPage';
import UserDashboardPage from './pages/UserDashboardPage';
import CreatorDashboardPage from './pages/CreatorDashboardPage';
import OAuthCallbackPage from './pages/OAuthCallbackPage';

function AppRoutes() {
  const { user, loading } = useAuth();

  if (loading) {
    return (
      <div className="page-loading">
        <div className="spinner" />
      </div>
    );
  }

  return (
    <>
      {user && <Nav />}
      <Routes>
        {/* Public */}
        <Route path="/login" element={user ? <Navigate to="/" replace /> : <LoginPage />} />
        <Route path="/auth/callback" element={<OAuthCallbackPage />} />

        {/* Protected — redirect to login if not authenticated */}
        <Route path="/" element={user ? <CatalogPage /> : <Navigate to="/login" replace />} />
        <Route path="/sessions/:id" element={user ? <SessionDetailPage /> : <Navigate to="/login" replace />} />
        <Route path="/dashboard" element={user ? <UserDashboardPage /> : <Navigate to="/login" replace />} />
        <Route
          path="/creator"
          element={
            user && user.role === 'creator'
              ? <CreatorDashboardPage />
              : user
                ? <Navigate to="/" replace />
                : <Navigate to="/login" replace />
          }
        />

        {/* Fallback */}
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <AppRoutes />
      </AuthProvider>
    </BrowserRouter>
  );
}
