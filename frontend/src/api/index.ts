/**
 * API call functions — thin wrappers around the Axios client.
 * All error handling happens at the call site (components/hooks).
 */
import api from './client';
import type { User, Session, CreatorSession, Booking, BookingList, SessionFormData } from '../types';

// ── Auth ──────────────────────────────────────────────────────────────────

export const authApi = {
  me: () => api.get<User>('/auth/me/'),
  logout: () => api.post('/auth/logout/'),
  updateProfile: (data: { name?: string; bio?: string }) =>
    api.patch<User>('/auth/profile/', data),

};

// ── Sessions ──────────────────────────────────────────────────────────────

export const sessionsApi = {
  list: () => api.get<Session[]>('/sessions/'),
  detail: (id: string) => api.get<Session>(`/sessions/${id}/`),
};

// ── Bookings ──────────────────────────────────────────────────────────────

export const bookingsApi = {
  book: (sessionId: string) => api.post<Booking>(`/sessions/${sessionId}/book/`),
  myBookings: () => api.get<BookingList>('/bookings/'),
};

// ── Creator ───────────────────────────────────────────────────────────────

export const creatorApi = {
  dashboard: () => api.get<CreatorSession[]>('/creator/dashboard/'),
  createSession: (data: SessionFormData) => api.post<Session>('/creator/sessions/', data),
  updateSession: (id: string, data: Partial<SessionFormData>) =>
    api.patch<Session>(`/creator/sessions/${id}/`, data),
  deleteSession: (id: string) => api.delete(`/creator/sessions/${id}/`),
};
