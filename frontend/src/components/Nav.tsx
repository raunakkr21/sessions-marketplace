import { Link, useLocation } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';

export default function Nav() {
  const { user, logout } = useAuth();
  const location = useLocation();

  const isActive = (path: string) =>
    location.pathname === path ? 'nav-link active' : 'nav-link';

  return (
    <nav className="nav">
      <div className="container nav-inner">
        <Link to="/" className="nav-logo">
          Sessions<span>Market</span>
        </Link>

        <div className="nav-links">
          <Link to="/" className={isActive('/')}>Browse</Link>

          {user?.role === 'creator' ? (
            <Link to="/creator" className={isActive('/creator')}>Creator Dashboard</Link>
          ) : (
            <Link to="/dashboard" className={isActive('/dashboard')}>My Bookings</Link>
          )}

          <div className="flex items-center gap-2">
            {user?.avatar_url && (
              <img src={user.avatar_url} alt={user.name} className="nav-avatar" />
            )}
            <span className="text-sm text-muted">{user?.name}</span>
            <button
              id="nav-logout-btn"
              onClick={logout}
              className="btn btn-ghost btn-sm"
            >
              Sign out
            </button>
          </div>
        </div>
      </div>
    </nav>
  );
}
