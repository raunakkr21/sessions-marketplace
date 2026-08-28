import { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';

/**
 * OAuthCallbackPage
 *
 * This page is the frontend destination after the backend processes the OAuth callback.
 * The backend has already set the JWT cookies on the response redirect.
 * We just need to refresh the auth context to pick up the new user.
 */
export default function OAuthCallbackPage() {
  const { refreshUser } = useAuth();
  const navigate = useNavigate();

  useEffect(() => {
    refreshUser().then(() => {
      navigate('/', { replace: true });
    }).catch(() => {
      navigate('/login?error=auth_failed', { replace: true });
    });
  }, [refreshUser, navigate]);

  return (
    <div className="page-loading">
      <div style={{ textAlign: 'center' }}>
        <div className="spinner" style={{ margin: '0 auto var(--spacing-4)' }} />
        <p className="text-muted">Completing sign in...</p>
      </div>
    </div>
  );
}
