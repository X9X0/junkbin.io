import api from './client';
import type {
  Product,
  Component,
  Schematic,
  User,
  PaginatedResponse,
  AuthTokens,
  LoginCredentials,
  RegisterData,
  ProductFilters,
  Report,
  ReportStats,
  UserReview,
} from '../types';

// Auth endpoints
export const auth = {
  // Get CSRF token cookie - must be called before any POST requests
  getCsrfToken: async (): Promise<void> => {
    await api.get('/auth/csrf/');
  },

  login: async (credentials: LoginCredentials): Promise<AuthTokens> => {
    const response = await api.post('/auth/token/', credentials);
    return response.data;
  },

  register: async (data: RegisterData): Promise<User> => {
    const response = await api.post('/auth/register/', data);
    return response.data;
  },

  me: async (): Promise<User> => {
    const response = await api.get('/auth/me/');
    return response.data;
  },

  refreshToken: async (): Promise<{ access: string }> => {
    // Token refresh uses HttpOnly cookies, no need to pass refresh token
    const response = await api.post('/auth/token/refresh/', {});
    return response.data;
  },

  logout: async (): Promise<void> => {
    await api.post('/auth/logout/', {});
  },
};

// Products endpoints
export const products = {
  list: async (filters?: ProductFilters): Promise<PaginatedResponse<Product>> => {
    const response = await api.get('/products/', { params: filters });
    return response.data;
  },

  get: async (id: string): Promise<Product> => {
    const response = await api.get(`/products/${id}/`);
    return response.data;
  },

  create: async (data: Partial<Product>): Promise<Product> => {
    const response = await api.post('/products/', data);
    return response.data;
  },

  update: async (id: string, data: Partial<Product>): Promise<Product> => {
    const response = await api.patch(`/products/${id}/`, data);
    return response.data;
  },

  featured: async (): Promise<Product[]> => {
    const response = await api.get('/products/featured/');
    return response.data;
  },

  recent: async (): Promise<Product[]> => {
    const response = await api.get('/products/recent/');
    return response.data;
  },

  components: async (id: string): Promise<any[]> => {
    const response = await api.get(`/products/${id}/components/`);
    return response.data;
  },

  schematics: async (id: string): Promise<Schematic[]> => {
    const response = await api.get(`/products/${id}/schematics/`);
    return response.data;
  },

  uploadImage: async (id: string, formData: FormData): Promise<any> => {
    const response = await api.post(`/products/${id}/upload_image/`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return response.data;
  },

  uploadSchematic: async (id: string, formData: FormData): Promise<Schematic> => {
    const response = await api.post(`/products/${id}/upload_schematic/`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return response.data;
  },

  addComponent: async (productId: string, data: any): Promise<any> => {
    const response = await api.post(`/products/${productId}/add_component/`, data);
    return response.data;
  },

  exportData: async (id: string): Promise<any> => {
    // Get product with all related data for export
    const [product, components, schematics] = await Promise.all([
      api.get(`/products/${id}/`),
      api.get(`/products/${id}/components/`),
      api.get(`/products/${id}/schematics/`),
    ]);
    return {
      product: product.data,
      components: components.data,
      schematics: schematics.data,
      exportedAt: new Date().toISOString(),
      source: 'junkbin.io',
    };
  },

  exportCsv: async (id: string): Promise<string> => {
    // Get product with components for CSV export
    const [product, components] = await Promise.all([
      api.get(`/products/${id}/`),
      api.get(`/products/${id}/components/`),
    ]);

    const p = product.data;
    const csvRows: string[] = [];

    // Header info
    csvRows.push(`# Product Export from junkbin.io`);
    csvRows.push(`# Exported: ${new Date().toISOString()}`);
    csvRows.push(`# Product: ${p.manufacturer} ${p.model_number}`);
    csvRows.push(``);

    // Components BOM
    csvRows.push(`Reference Designator,Part Number,Manufacturer,Type,Package,Quantity,Location,Notes`);

    components.data.forEach((pc: any) => {
      const row = [
        pc.reference_designator || '',
        pc.component?.part_number || '',
        pc.component?.manufacturer || '',
        pc.component?.component_type_display || pc.component?.component_type || '',
        pc.component?.package_type || '',
        pc.quantity || 1,
        pc.location_description || '',
        (pc.notes || '').replace(/"/g, '""'),
      ];
      csvRows.push(row.map(v => `"${v}"`).join(','));
    });

    return csvRows.join('\n');
  },
};

// Components endpoints
export const components = {
  list: async (params?: any): Promise<PaginatedResponse<Component>> => {
    const response = await api.get('/components/', { params });
    return response.data;
  },

  get: async (id: string): Promise<Component> => {
    const response = await api.get(`/components/${id}/`);
    return response.data;
  },

  search: async (query: string): Promise<Component[]> => {
    const response = await api.get('/components/', { params: { search: query } });
    return response.data.results;
  },

  crossReference: async (id: string): Promise<Product[]> => {
    const response = await api.get(`/components/${id}/products/`);
    return response.data.results || response.data;
  },
};

// Schematics endpoints
export const schematics = {
  list: async (params?: any): Promise<PaginatedResponse<Schematic>> => {
    const response = await api.get('/schematics/', { params });
    return response.data;
  },

  get: async (id: string): Promise<Schematic> => {
    const response = await api.get(`/schematics/${id}/`);
    return response.data;
  },

  download: async (id: string): Promise<{ download_url: string }> => {
    const response = await api.get(`/schematics/${id}/download/`);
    return response.data;
  },

  recent: async (): Promise<Schematic[]> => {
    const response = await api.get('/schematics/recent/');
    return response.data;
  },
};

// Search endpoint
export const search = {
  global: async (query: string): Promise<any> => {
    const response = await api.get('/search/', { params: { q: query } });
    const data = response.data;
    // Flatten nested pagination: { results: { products: { results: [...] } } }
    // into the shape components expect: { products: [...], components: [...], schematics: [...] }
    const r = data.results || data;
    return {
      products: r.products?.results || r.products || [],
      components: r.components?.results || r.components || [],
      schematics: r.schematics?.results || r.schematics || [],
    };
  },
};

// Stats endpoint
export const stats = {
  get: async (): Promise<{
    products: number;
    components: number;
    schematics: number;
    contributors: number;
  }> => {
    const response = await api.get('/stats/');
    return response.data;
  },
};

// Reports endpoints (moderation)
export const reports = {
  list: async (params?: any): Promise<PaginatedResponse<Report>> => {
    const response = await api.get('/reports/', { params });
    return response.data;
  },

  get: async (id: string): Promise<Report> => {
    const response = await api.get(`/reports/${id}/`);
    return response.data;
  },

  pending: async (params?: any): Promise<PaginatedResponse<Report>> => {
    const response = await api.get('/reports/pending/', { params });
    return response.data;
  },

  resolve: async (id: string, data: { action: string; notes?: string }): Promise<Report> => {
    const response = await api.post(`/reports/${id}/resolve/`, data);
    return response.data;
  },

  stats: async (): Promise<ReportStats> => {
    const response = await api.get('/reports/stats/');
    return response.data;
  },
};

// User reviews endpoints (moderation)
export const reviews = {
  list: async (params?: any): Promise<PaginatedResponse<UserReview>> => {
    const response = await api.get('/user-reviews/', { params });
    return response.data;
  },

  pending: async (params?: any): Promise<PaginatedResponse<UserReview>> => {
    const response = await api.get('/user-reviews/pending/', { params });
    return response.data;
  },

  get: async (id: string): Promise<UserReview> => {
    const response = await api.get(`/user-reviews/${id}/`);
    return response.data;
  },

  start: async (id: string): Promise<UserReview> => {
    const response = await api.post(`/user-reviews/${id}/start_review/`);
    return response.data;
  },

  complete: async (id: string, data: { status: string; notes?: string; action_taken?: string }): Promise<UserReview> => {
    const response = await api.post(`/user-reviews/${id}/complete/`, data);
    return response.data;
  },
};

// Users endpoints (leaderboard)
export const users = {
  list: async (params?: Record<string, any>): Promise<PaginatedResponse<User>> => {
    const response = await api.get('/users/', { params });
    return response.data;
  },
};

// Newsletter endpoint
export const newsletter = {
  subscribe: async (email: string, source: string = 'landing'): Promise<{ message: string; email: string }> => {
    const response = await api.post('/newsletter/subscribe/', { email, source });
    return response.data;
  },
};
