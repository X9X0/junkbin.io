import axios from 'axios';
import i18n from '../i18n';

// Use relative URL in production (works with nginx proxy), localhost for dev
const API_URL = import.meta.env.VITE_API_URL || '/api';

// Helper to get CSRF token from cookies
function getCsrfToken(): string | null {
  const name = 'csrftoken';
  const cookies = document.cookie.split(';');
  for (const cookie of cookies) {
    const [cookieName, cookieValue] = cookie.trim().split('=');
    if (cookieName === name) {
      return cookieValue;
    }
  }
  return null;
}

export const api = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  // Include cookies with requests for HttpOnly token auth
  withCredentials: true,
});

// Request interceptor to add CSRF token and Accept-Language
api.interceptors.request.use((config) => {
  const csrfToken = getCsrfToken();
  if (csrfToken) {
    config.headers['X-CSRFToken'] = csrfToken;
  }
  config.headers['Accept-Language'] = i18n.language || 'en';
  return config;
});

// Response interceptor for token refresh
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;

    // Skip refresh logic for auth endpoints to prevent infinite loops
    const skipRefreshUrls = ['/auth/me/', '/auth/token/', '/auth/token/refresh/', '/auth/csrf/'];
    const shouldSkipRefresh = skipRefreshUrls.some(url => originalRequest.url?.includes(url));

    // Only a 401 means "not authenticated" in this app's DRF config (missing or
    // invalid token) — a silent refresh+retry can actually fix that. A 403 always
    // means the user IS authenticated but a specific permission check failed for
    // a real reason (unverified email, not a moderator, not the owner, etc.);
    // refreshing the token can't change that, so retrying just wastes a round
    // trip and needlessly rotates the refresh token (ROTATE_REFRESH_TOKENS is on).
    if (error.response?.status === 401 && !originalRequest._retry && !shouldSkipRefresh) {
      originalRequest._retry = true;

      try {
        // Token refresh uses HttpOnly cookies automatically
        await axios.post(
          `${API_URL}/auth/token/refresh/`,
          {},
          { withCredentials: true }
        );

        // Retry original request - new token is in cookie
        return api(originalRequest);
      } catch (refreshError) {
        // Refresh failed - don't redirect, just reject
        return Promise.reject(refreshError);
      }
    }

    return Promise.reject(error);
  }
);

export default api;
