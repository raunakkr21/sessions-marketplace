/**
 * TypeScript interfaces matching the backend API response shapes.
 */

export interface User {
  id: string;
  email: string;
  name: string;
  bio: string;
  avatar_url: string;
  role: 'user' | 'creator';
  created_at: string;
}

export interface Session {
  id: string;
  title: string;
  description: string;
  creator: User;
  start_time: string;
  end_time: string;
  capacity: number;
  active_booking_count: number;
  remaining_seats: number;
  has_started: boolean;
  created_at: string;
  updated_at: string;
}

/** Creator's own session with booking counts */
export interface CreatorSession {
  id: string;
  title: string;
  description: string;
  start_time: string;
  end_time: string;
  capacity: number;
  booking_count: number;
  remaining_seats: number;
  has_started: boolean;
  created_at: string;
  updated_at: string;
}

export interface Booking {
  id: string;
  session: Session;
  status: 'active' | 'cancelled';
  created_at: string;
  updated_at: string;
}

export interface BookingList {
  active: Booking[];
  past: Booking[];
}

export interface ApiError {
  error: string;
  detail: string | Record<string, string[]>;
}

export interface SessionFormData {
  title: string;
  description: string;
  start_time: string;
  end_time: string;
  capacity: number;
}
