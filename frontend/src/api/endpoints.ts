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
} from '../types';

// Auth endpoints
export const auth = {
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

  refreshToken: async (refresh: string): Promise<{ access: string }> => {
    const response = await api.post('/auth/token/refresh/', { refresh });
    return response.data;
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
    const response = await api.get(`/components/${id}/cross_reference/`);
    return response.data;
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
    return response.data;
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
