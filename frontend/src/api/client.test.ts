import { describe, it, expect, vi, beforeEach } from 'vitest';
import { server } from '../test/mocks/server';
import { http, HttpResponse } from 'msw';
import api from './client';

const API_URL = 'http://localhost/api';

describe('API Client', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    document.cookie = 'csrftoken=; expires=Thu, 01 Jan 1970 00:00:00 GMT';
  });

  describe('request headers', () => {
    it('does not add Authorization header (uses cookie auth)', async () => {
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

    it('adds X-CSRFToken header when csrftoken cookie is set', async () => {
      document.cookie = 'csrftoken=test-csrf-token';

      let capturedHeaders: Headers | undefined;
      server.use(
        http.get(`${API_URL}/test/`, ({ request }) => {
          capturedHeaders = request.headers;
          return HttpResponse.json({ success: true });
        })
      );

      await api.get('/test/');

      expect(capturedHeaders!.get('X-CSRFToken')).toBe('test-csrf-token');
    });

    it('adds Accept-Language header', async () => {
      let capturedHeaders: Headers | undefined;
      server.use(
        http.get(`${API_URL}/test/`, ({ request }) => {
          capturedHeaders = request.headers;
          return HttpResponse.json({ success: true });
        })
      );

      await api.get('/test/');

      expect(capturedHeaders!.get('Accept-Language')).toBeTruthy();
    });
  });

  describe('token refresh', () => {
    it('attempts cookie refresh on 401 response', async () => {
      let refreshCalled = false;
      let requestCount = 0;

      server.use(
        http.get(`${API_URL}/protected/`, () => {
          requestCount++;
          if (requestCount === 1) {
            return HttpResponse.json({ detail: 'Unauthorized' }, { status: 401 });
          }
          return HttpResponse.json({ data: 'success' });
        }),
        http.post(`${API_URL}/auth/token/refresh/`, () => {
          refreshCalled = true;
          return HttpResponse.json({});
        })
      );

      const response = await api.get('/protected/');

      expect(refreshCalled).toBe(true);
      expect(response.data).toEqual({ data: 'success' });
      expect(requestCount).toBe(2);
    });

    it('rejects without redirect when refresh fails', async () => {
      server.use(
        http.get(`${API_URL}/protected/`, () => {
          return HttpResponse.json({ detail: 'Unauthorized' }, { status: 401 });
        }),
        http.post(`${API_URL}/auth/token/refresh/`, () => {
          return HttpResponse.json({ detail: 'Invalid token' }, { status: 401 });
        })
      );

      let threw = false;
      try {
        await api.get('/protected/');
      } catch {
        threw = true;
      }

      expect(threw).toBe(true);
      // Cookie auth never redirects to /login
      expect(window.location.pathname).not.toBe('/login');
    });

    it('does not retry auth endpoints on 401', async () => {
      let refreshCalled = false;

      server.use(
        http.get(`${API_URL}/auth/me/`, () => {
          return HttpResponse.json({ detail: 'Unauthorized' }, { status: 401 });
        }),
        http.post(`${API_URL}/auth/token/refresh/`, () => {
          refreshCalled = true;
          return HttpResponse.json({});
        })
      );

      let threw = false;
      try {
        await api.get('/auth/me/');
      } catch {
        threw = true;
      }

      expect(threw).toBe(true);
      expect(refreshCalled).toBe(false);
    });

    it('does not retry the same request twice', async () => {
      let requestCount = 0;

      server.use(
        http.get(`${API_URL}/protected/`, () => {
          requestCount++;
          return HttpResponse.json({ detail: 'Unauthorized' }, { status: 401 });
        }),
        http.post(`${API_URL}/auth/token/refresh/`, () => {
          return HttpResponse.json({});
        })
      );

      let threw = false;
      try {
        await api.get('/protected/');
      } catch {
        threw = true;
      }

      expect(threw).toBe(true);
      expect(requestCount).toBe(2); // original + one retry
    });
  });

  describe('error handling', () => {
    it('rejects on network error', async () => {
      server.use(
        http.get(`${API_URL}/error/`, () => {
          return HttpResponse.error();
        })
      );

      let threw = false;
      try {
        await api.get('/error/');
      } catch {
        threw = true;
      }

      expect(threw).toBe(true);
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

      let threw = false;
      try {
        await api.get('/server-error/');
      } catch {
        threw = true;
      }

      expect(threw).toBe(true);
    });
  });
});
