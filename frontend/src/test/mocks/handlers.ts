import { http, HttpResponse } from 'msw';

const API_URL = 'http://localhost:8000/api';

// Test data
export const mockUser = {
  id: 'test-user-id',
  username: 'testuser',
  email: 'test@example.com',
  reputation_score: 100,
  contribution_count: 10,
  is_trusted: false,
  is_moderator: false,
  created_at: '2024-01-01T00:00:00Z',
};

export const mockTokens = {
  access: 'mock-access-token',
  refresh: 'mock-refresh-token',
};

export const mockProduct = {
  id: 'product-1',
  manufacturer: 'Test Manufacturer',
  model_number: 'TEST-001',
  category: 'router',
  is_approved: true,
  is_featured: false,
  component_count: 5,
  image_count: 2,
  schematic_count: 1,
  created_at: '2024-01-01T00:00:00Z',
};

export const mockComponent = {
  id: 'component-1',
  part_number: 'TEST123',
  manufacturer: 'Test Corp',
  component_type: 'ic',
  component_type_display: 'Integrated Circuit',
  description: 'Test component',
  package_type: 'SOIC-8',
  usage_count: 10,
  is_verified: true,
};

// Request handlers
export const handlers = [
  // Auth endpoints
  http.post(`${API_URL}/auth/token/`, async ({ request }) => {
    const body = await request.json() as { username: string; password: string };

    if (body.username === 'testuser' && body.password === 'testpass') {
      return HttpResponse.json(mockTokens);
    }

    if (body.username === 'baduser') {
      return HttpResponse.json(
        { detail: 'Invalid credentials' },
        { status: 401 }
      );
    }

    return HttpResponse.json(mockTokens);
  }),

  http.post(`${API_URL}/auth/token/refresh/`, async ({ request }) => {
    const body = await request.json() as { refresh: string };

    if (body.refresh === 'invalid-refresh-token') {
      return HttpResponse.json(
        { detail: 'Token is invalid or expired' },
        { status: 401 }
      );
    }

    return HttpResponse.json({ access: 'new-access-token' });
  }),

  http.post(`${API_URL}/auth/register/`, async ({ request }) => {
    const body = await request.json() as { username: string; email: string };

    if (body.username === 'existinguser') {
      return HttpResponse.json(
        { username: ['A user with that username already exists.'] },
        { status: 400 }
      );
    }

    return HttpResponse.json(mockUser, { status: 201 });
  }),

  http.get(`${API_URL}/auth/me/`, ({ request }) => {
    const authHeader = request.headers.get('Authorization');

    if (!authHeader || authHeader === 'Bearer invalid-token') {
      return HttpResponse.json(
        { detail: 'Authentication credentials were not provided.' },
        { status: 401 }
      );
    }

    return HttpResponse.json(mockUser);
  }),

  // Products endpoints
  http.get(`${API_URL}/products/`, () => {
    return HttpResponse.json({
      count: 1,
      next: null,
      previous: null,
      results: [mockProduct],
    });
  }),

  http.get(`${API_URL}/products/:id/`, ({ params }) => {
    return HttpResponse.json({
      ...mockProduct,
      id: params.id,
    });
  }),

  http.post(`${API_URL}/products/`, async ({ request }) => {
    const body = await request.json();
    return HttpResponse.json(
      { ...mockProduct, ...body },
      { status: 201 }
    );
  }),

  http.post(`${API_URL}/products/:id/add_component/`, async () => {
    return HttpResponse.json(
      { id: 'pc-1', component: mockComponent },
      { status: 201 }
    );
  }),

  http.post(`${API_URL}/products/:id/upload_image/`, async () => {
    return HttpResponse.json(
      { id: 'img-1', image: '/images/test.jpg' },
      { status: 201 }
    );
  }),

  // Components endpoints
  http.get(`${API_URL}/components/`, ({ request }) => {
    const url = new URL(request.url);
    const search = url.searchParams.get('search');

    if (search === 'notfound') {
      return HttpResponse.json({
        count: 0,
        next: null,
        previous: null,
        results: [],
      });
    }

    return HttpResponse.json({
      count: 1,
      next: null,
      previous: null,
      results: [mockComponent],
    });
  }),

  http.post(`${API_URL}/components/`, async ({ request }) => {
    const body = await request.json();
    return HttpResponse.json(
      { ...mockComponent, ...body },
      { status: 201 }
    );
  }),

  // Stats endpoint
  http.get(`${API_URL}/stats/`, () => {
    return HttpResponse.json({
      products: 100,
      components: 500,
      schematics: 50,
      contributors: 25,
    });
  }),

  // Search endpoint
  http.get(`${API_URL}/search/`, ({ request }) => {
    const url = new URL(request.url);
    const query = url.searchParams.get('q');

    return HttpResponse.json({
      products: query ? [mockProduct] : [],
      components: query ? [mockComponent] : [],
    });
  }),
];
