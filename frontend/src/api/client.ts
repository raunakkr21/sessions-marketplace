/**
 * Axios instance configured for the API.
 *
 * Key decisions:
 * - withCredentials: true — sends HttpOnly cookies with every request
 * - Interceptor auto-refreshes access token on 401 (transparent to callers)
 * - On refresh failure, clears auth state and redirects to login
 */
import axios, { AxiosError } from 'axios';

const api = axios.create({
  baseURL: '/api',
  withCredentials: true, // Required to send/receive HttpOnly cookies
  headers: {
    'Content-Type': 'application/json',
  },
});

// Track in-flight refresh to prevent multiple simultaneous refresh attempts
let isRefreshing = false;
let pendingRequests: Array<{ resolve: (value: unknown) => void; reject: (reason?: any) => void }> = [];

function onRefreshed() {
  pendingRequests.forEach(p => p.resolve(undefined));
  pendingRequests = [];
}

api.interceptors.response.use(
  response => response,
  async (error: AxiosError) => {
    const originalRequest = error.config as typeof error.config & { _retry?: boolean };

    // Only attempt refresh on 401, and only once per request
    if (error.response?.status === 401 && !originalRequest?._retry) {
      if (isRefreshing) {
        // Queue requests while refresh is in progress
        return new Promise((resolve, reject) => {
          pendingRequests.push({ resolve, reject });
        }).then(() => api(originalRequest!));
      }

      originalRequest!._retry = true;
      isRefreshing = true;

      try {
        await axios.post('/api/auth/token/refresh/', {}, { withCredentials: true });
        onRefreshed();
        isRefreshing = false;
        return api(originalRequest!);
      } catch (refreshError) {
        // Refresh failed — user needs to log in again
        isRefreshing = false;
        pendingRequests.forEach(p => p.reject(refreshError));
        pendingRequests = [];
        
        // Prevent infinite reload loop if already on login page
        // Skip redirect for /auth/me/ so AuthProvider can handle initial load without forcing an error
        if (!window.location.pathname.startsWith('/login') && originalRequest.url !== '/auth/me/') {
          window.location.href = '/login?error=session_expired';
        }
        return Promise.reject(refreshError);
      }
    }

    return Promise.reject(error);
  }
);

export default api;
