import { useSearchParams } from 'react-router-dom';

const ERROR_MESSAGES: Record<string, string> = {
  oauth_cancelled: 'Sign-in was cancelled. Please try again.',
  no_code: 'OAuth authorisation code was not received.',
  invalid_state: 'Security check failed. Please try again.',
  token_exchange_failed: 'Could not exchange authorisation code. Check your credentials.',
  userinfo_failed: 'Could not fetch your Google profile.',
  email_not_verified: 'Your Google account email is not verified.',
  session_expired: 'Your session has expired. Please sign in again.',
};

export default function LoginPage() {
  const [params] = useSearchParams();
  const errorKey = params.get('error');
  const errorMessage = errorKey ? ERROR_MESSAGES[errorKey] : null;

  return (
    <div style={{
      minHeight: '100vh',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      padding: 'var(--spacing-6)',
    }}>
      <div style={{ maxWidth: 420, width: '100%' }}>

        {/* Logo / Hero */}
        <div className="text-center mb-6" style={{ marginBottom: 'var(--spacing-8)' }}>
          <h1 style={{
            fontSize: 'var(--font-size-3xl)',
            fontWeight: 700,
            color: 'var(--color-text)',
            lineHeight: 1.2,
          }}>
            Sessions<span style={{ color: 'var(--color-primary)' }}>Market</span>
          </h1>
          <p style={{
            marginTop: 'var(--spacing-3)',
            color: 'var(--color-text-muted)',
            fontSize: 'var(--font-size-lg)',
          }}>
            Book expert-led sessions on topics you care about.
          </p>
        </div>

        {/* Card */}
        <div className="card" style={{ display: 'flex', flexDirection: 'column', gap: 'var(--spacing-6)' }}>

          {/* Error message from OAuth failure */}
          {errorMessage && (
            <div className="alert alert-error" role="alert">
              ⚠️ {errorMessage}
            </div>
          )}

          <div>
            <h2 style={{ fontSize: 'var(--font-size-xl)', fontWeight: 600, marginBottom: 'var(--spacing-2)' }}>
              Welcome back
            </h2>
            <p className="text-sm text-muted">
              Sign in with your Google account to continue.
            </p>
          </div>

          <a
            id="google-signin-btn"
            href="/api/auth/google/"
            className="btn btn-primary btn-lg"
            style={{ justifyContent: 'center', gap: 'var(--spacing-3)' }}
          >
            {/* Google G logo */}
            <svg width="20" height="20" viewBox="0 0 48 48" aria-hidden="true">
              <path fill="#FFC107" d="M43.611,20.083H42V20H24v8h11.303c-1.649,4.657-6.08,8-11.303,8c-6.627,0-12-5.373-12-12c0-6.627,5.373-12,12-12c3.059,0,5.842,1.154,7.961,3.039l5.657-5.657C34.046,6.053,29.268,4,24,4C12.955,4,4,12.955,4,24c0,11.045,8.955,20,20,20c11.045,0,20-8.955,20-20C44,22.659,43.862,21.35,43.611,20.083z"/>
              <path fill="#FF3D00" d="M6.306,14.691l6.571,4.819C14.655,15.108,18.961,12,24,12c3.059,0,5.842,1.154,7.961,3.039l5.657-5.657C34.046,6.053,29.268,4,24,4C16.318,4,9.656,8.337,6.306,14.691z"/>
              <path fill="#4CAF50" d="M24,44c5.166,0,9.86-1.977,13.409-5.192l-6.19-5.238C29.211,35.091,26.715,36,24,36c-5.202,0-9.619-3.317-11.283-7.946l-6.522,5.025C9.505,39.556,16.227,44,24,44z"/>
              <path fill="#1976D2" d="M43.611,20.083H42V20H24v8h11.303c-0.792,2.237-2.231,4.166-4.087,5.571c0.001-0.001,0.002-0.001,0.003-0.002l6.19,5.238C36.971,39.205,44,34,44,24C44,22.659,43.862,21.35,43.611,20.083z"/>
            </svg>
            Continue with Google
          </a>

          <hr className="divider" />

          <div className="text-sm text-muted text-center" style={{ textAlign: 'center' }}>
            <p><strong style={{ color: 'var(--color-text)' }}>For Users:</strong> Browse and book sessions.</p>
            <p style={{ marginTop: 'var(--spacing-1)' }}><strong style={{ color: 'var(--color-text)' }}>For Creators:</strong> Create and manage your sessions.</p>
            <p style={{ marginTop: 'var(--spacing-3)', fontSize: 'var(--font-size-xs)' }}>
              Creator accounts are assigned by an admin.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
