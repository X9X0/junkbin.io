import { describe, it, expect, vi, beforeEach } from 'vitest';
import { server } from '../test/mocks/server';
import { http, HttpResponse } from 'msw';
import api from './client';

const API_URL = 'http://localhost:8000/api';

describe('API Client', () => {
  beforeEach(() => {
    localStorage.clear();
    vi.clearAllMocks();
  });

  describe('authorization header', () => {
    it('adds Authorization header when token exists', async () => {
      localStorage.setItem('access_token', 'my-access-token');

      let capturedHeaders: Headers | undefined;
      server.use(
        http.get(`${API_URL}/test/`, ({ request }) => {
          capturedHeaders = request.headers;
          return HttpResponse.json({ success: true });
        })
      );

      await api.get('/test/');

      expect(capturedHeaders!.get('Authorization')).toBe('Bearer my-access-token');
    });

    it('does not add Authorization header when no token', async () => {
      let capturedHeaders: Headers | undefined;
      server.use(
        http.get(`${API_URL}/test/`, ({ request }) => {
          capturedHeaders = request.headers;
          return HttpResponse.json({ success: true });
        })
      );

      await api.get('/test/');

      expect(capturedHeaders!.get('Authorization')).toBeNull();
    });
  });

  describe('token refresh', () => {
    it('attempts token refresh on 401 response', async () => {
      localStorage.setItem('access_token', 'expired-token');
      localStorage.setItem('refresh_token', 'valid-refresh-token');

      let requestCount = 0;
      server.use(
        http.get(`${API_URL}/protected/`, ({ request }) => {
          requestCount++;
          const auth = request.headers.get('Authorization');

          // First request fails, retry after refresh succeeds
          if (auth === 'Bearer expired-token') {
            return HttpResponse.json(
              { detail: 'Token expired' },
              { status: 401 }
            );
          }

          return HttpResponse.json({ data: 'success' });
        }),
        http.post(`${API_URL}/auth/token/refresh/`, () => {
          return HttpResponse.json({ access: 'new-access-token' });
        })
      );

      const response = await api.get('/protected/');

      expect(response.data).toEqual({ data: 'success' });
      expect(localStorage.getItem('access_token')).toBe('new-access-token');
      expect(requestCount).toBe(2); // Original + retry
    });

    it('redirects to login when refresh fails', async () => {
      localStorage.setItem('access_token', 'expired-token');
      localStorage.setItem('refresh_token', 'invalid-refresh-token');

      // Mock window.location
      const originalHref = window.location.href;
      Object.defineProperty(window, 'location', {
        value: { href: '' },
        writable: true,
      });

      server.use(
        http.get(`${API_URL}/protected/`, () => {
          return HttpResponse.json(
            { detail: 'Token expired' },
            { status: 401 }
          );
        }),
        http.post(`${API_URL}/auth/token/refresh/`, () => {
          return HttpResponse.json(
            { detail: 'Invalid token' },
            { status: 401 }
          );
        })
      );

      try {
        await api.get('/protected/');
      } catch (error) {
        // Expected to throw
      }

      expect(localStorage.getItem('access_token')).toBeNull();
      expect(localStorage.getItem('refresh_token')).toBeNull();
      expect(window.location.href).toBe('/login');

      // Restore window.location
      Object.defineProperty(window, 'location', {
        value: { href: originalHref },
        writable: true,
      });
    });

    it('does not retry if no refresh token exists', async () => {
      localStorage.setItem('access_token', 'expired-token');
      // No refresh token set

      let requestCount = 0;
      server.use(
        http.get(`${API_URL}/protected/`, () => {
          requestCount++;
          return HttpResponse.json(
            { detail: 'Token expired' },
            { status: 401 }
          );
        })
      );

      await expect(api.get('/protected/')).rejects.toThrow();

      expect(requestCount).toBe(1); // No retry without refresh token
    });

    it('does not retry same request twice', async () => {
      localStorage.setItem('access_token', 'expired-token');
      localStorage.setItem('refresh_token', 'valid-refresh-token');

      let requestCount = 0;
      server.use(
        http.get(`${API_URL}/protected/`, () => {
          requestCount++;
          return HttpResponse.json(
            { detail: 'Token expired' },
            { status: 401 }
          );
        }),
        http.post(`${API_URL}/auth/token/refresh/`, () => {
          return HttpResponse.json({ access: 'still-bad-token' });
        })
      );

      await expect(api.get('/protected/')).rejects.toThrow();

      // Should only try twice: original + one retry
      expect(requestCount).toBe(2);
    });
  });

  describe('error handling', () => {
    it('rejects on network error', async () => {
      server.use(
        http.get(`${API_URL}/error/`, () => {
          return HttpResponse.error();
        })
      );

      await expect(api.get('/error/')).rejects.toThrow();
    });

    it('rejects on 500 server error', async () => {
      server.use(
        http.get(`${API_URL}/server-error/`, () => {
          return HttpResponse.json(
            { detail: 'Internal server error' },
            { status: 500 }
          );
        })
      );

      await expect(api.get('/server-error/')).rejects.toThrow();
    });
  });
});
