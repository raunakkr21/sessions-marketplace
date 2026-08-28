/**
 * Utility: extract a human-readable error message from an Axios error.
 */
import type { AxiosError } from 'axios';
import type { ApiError } from '../types';

export function getErrorMessage(error: unknown): string {
  const axiosError = error as AxiosError<ApiError>;
  const data = axiosError?.response?.data;

  if (!data) {
    return 'An unexpected error occurred. Please try again.';
  }

  const detail = data.detail;
  if (typeof detail === 'string') return detail;
  if (typeof detail === 'object') {
    // Field-level validation errors
    return Object.entries(detail)
      .map(([field, msgs]) => `${field}: ${Array.isArray(msgs) ? msgs.join(', ') : msgs}`)
      .join(' | ');
  }
  return 'An error occurred.';
}

/**
 * Format a UTC datetime string for display in the user's local time zone.
 */
export function formatDateTime(isoString: string): string {
  return new Date(isoString).toLocaleString(undefined, {
    dateStyle: 'medium',
    timeStyle: 'short',
  });
}

/**
 * Format just the date portion.
 */
export function formatDate(isoString: string): string {
  return new Date(isoString).toLocaleDateString(undefined, { dateStyle: 'medium' });
}

/**
 * Format a relative time (e.g., "in 3 days").
 */
export function formatRelativeTime(isoString: string): string {
  const now = Date.now();
  const then = new Date(isoString).getTime();
  const diff = then - now;

  const abs = Math.abs(diff);
  const minutes = Math.round(abs / 60000);
  const hours = Math.round(abs / 3600000);
  const days = Math.round(abs / 86400000);

  const suffix = diff < 0 ? ' ago' : '';
  const prefix = diff < 0 ? '' : 'in ';

  if (minutes < 60) return `${prefix}${minutes}m${suffix}`;
  if (hours < 24)   return `${prefix}${hours}h${suffix}`;
  return `${prefix}${days}d${suffix}`;
}

/**
 * Compute a color for the seats bar based on fill percentage.
 */
export function seatsBarColor(remaining: number, capacity: number): string {
  const pct = capacity > 0 ? remaining / capacity : 0;
  if (pct > 0.5) return 'var(--color-success)';
  if (pct > 0.2) return 'var(--color-warning)';
  return 'var(--color-danger)';
}
