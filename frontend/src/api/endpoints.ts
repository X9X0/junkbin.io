import api from './client';
import type {
  Product,
  ProductImage,
  ProductComment,
  RepairReport,
  ProductComponent,
  Component,
  ComponentImage,
  Schematic,
  Firmware,
  ComponentSuggestion,
  BomCandidate,
  User,
  PublicUser,
  UserStats,
  UserContributions,
  PaginatedResponse,
  AuthTokens,
  LoginCredentials,
  RegisterData,
  ProductFilters,
  Report,
  ReportStats,
  UserReview,
  Conversation,
  Message,
  UserBlock,
  AppNotification,
  UserPreferences,
  JunkbinItem,
  JunkbinSummary,
  JunkbinCheckResponse,
  Recipe,
  RecipeMatchDetail,
  NexarData,
  AnalyticsDashboardData,
  BackgroundRemovalPreview,
  BackgroundRemovalParams,
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

  googleLogin: async (credential: string): Promise<{ user: User; created: boolean }> => {
    const response = await api.post('/auth/google/', { credential });
    return response.data;
  },

  githubLogin: async (code: string): Promise<{ user: User; created: boolean }> => {
    const response = await api.post('/auth/github/', { code });
    return response.data;
  },

  getPreferences: async (): Promise<UserPreferences> => {
    const response = await api.get('/auth/preferences/');
    return response.data;
  },

  updatePreferences: async (data: Partial<UserPreferences>): Promise<UserPreferences> => {
    const response = await api.patch('/auth/preferences/', data);
    return response.data;
  },

  updateProfile: async (data: FormData): Promise<User> => {
    const response = await api.patch('/auth/me/', data, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return response.data;
  },

  updateMe: async (data: Record<string, unknown>): Promise<User> => {
    const response = await api.patch('/auth/me/', data);
    return response.data;
  },

  changePassword: async (data: { current_password: string; new_password: string; new_password_confirm: string }): Promise<void> => {
    await api.post('/auth/password/change/', data);
  },

  changeUsername: async (data: { current_password: string; new_username: string }): Promise<User> => {
    const response = await api.post('/auth/username/change/', data);
    return response.data;
  },

  deleteAccount: async (data: { current_password: string }): Promise<void> => {
    await api.post('/auth/account/delete/', data);
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

  delete: async (id: string): Promise<void> => {
    await api.delete(`/products/${id}/`);
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

  firmware: async (id: string): Promise<Firmware[]> => {
    const response = await api.get(`/products/${id}/firmware/`);
    return response.data;
  },

  uploadImage: async (id: string, formData: FormData): Promise<any> => {
    const response = await api.post(`/products/${id}/upload_image/`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return response.data;
  },

  comments: async (id: string, page?: number): Promise<PaginatedResponse<ProductComment>> => {
    const response = await api.get(`/products/${id}/comments/`, { params: { page } });
    return response.data;
  },

  addComment: async (id: string, content: string): Promise<ProductComment> => {
    const response = await api.post(`/products/${id}/comments/`, { content });
    return response.data;
  },

  deleteComment: async (productId: string, commentId: string): Promise<void> => {
    await api.delete(`/products/${productId}/comments/${commentId}/`);
  },

  repairs: async (id: string, page?: number): Promise<PaginatedResponse<RepairReport>> => {
    const response = await api.get(`/products/${id}/repairs/`, { params: { page } });
    return response.data;
  },

  addRepairReport: async (id: string, data: {
    title: string;
    symptom: string;
    diagnostics?: string;
    resolution?: string;
    status?: string;
    product_component?: string | null;
  }): Promise<RepairReport> => {
    const response = await api.post(`/products/${id}/repairs/`, data);
    return response.data;
  },

  deleteRepairReport: async (productId: string, reportId: string): Promise<void> => {
    await api.delete(`/products/${productId}/repairs/${reportId}/`);
  },

  voteRepairReport: async (
    productId: string,
    reportId: string,
    voteType: 'helpful' | 'not_helpful'
  ): Promise<RepairReport> => {
    const response = await api.post(`/products/${productId}/repairs/${reportId}/vote/`, {
      vote_type: voteType,
    });
    return response.data;
  },

  removeRepairReportVote: async (productId: string, reportId: string): Promise<RepairReport> => {
    const response = await api.delete(`/products/${productId}/repairs/${reportId}/vote/`);
    return response.data;
  },

  uploadSchematic: async (id: string, formData: FormData): Promise<Schematic> => {
    const response = await api.post(`/products/${id}/upload_schematic/`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return response.data;
  },

  uploadFirmware: async (id: string, formData: FormData): Promise<Firmware> => {
    const response = await api.post(`/products/${id}/upload_firmware/`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return response.data;
  },

  extractBomPdf: async (id: string, formData: FormData): Promise<{
    candidates: BomCandidate[];
    total: number;
    high_confidence: number;
    low_confidence: number;
  }> => {
    const response = await api.post(`/products/${id}/extract_bom_pdf/`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return response.data;
  },

  submitBomSuggestions: async (id: string, candidates: BomCandidate[], sourceType?: string): Promise<{ created: number; detail: string }> => {
    const response = await api.post(`/products/${id}/submit_bom_suggestions/`, { candidates, source_type: sourceType });
    return response.data;
  },

  addComponent: async (productId: string, data: any): Promise<any> => {
    const response = await api.post(`/products/${productId}/add_component/`, data);
    return response.data;
  },

  parseBom: async (id: string, formData: FormData): Promise<any> => {
    const response = await api.post(`/products/${id}/parse_bom/`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return response.data;
  },

  importBom: async (id: string, formData: FormData): Promise<any> => {
    const response = await api.post(`/products/${id}/import_bom/`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return response.data;
  },

  batchAddComponents: async (id: string, data: { components: any[] }): Promise<any> => {
    const response = await api.post(`/products/${id}/batch_add_components/`, data);
    return response.data;
  },

  approve: async (id: string): Promise<{ detail: string }> => {
    const response = await api.post(`/products/${id}/approve/`);
    return response.data;
  },

  reject: async (id: string): Promise<void> => {
    await api.post(`/products/${id}/reject/`);
  },

  pendingCounts: async (): Promise<{ products: number; schematics: number; firmware: number; recipes: number; images: number; component_images: number; datasheets: number; component_suggestions: number }> => {
    const response = await api.get('/products/pending_counts/');
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

  create: async (data: Partial<Component>): Promise<Component> => {
    const response = await api.post('/components/', data);
    return response.data;
  },

  update: async (id: string, data: Partial<Component>): Promise<Component> => {
    const response = await api.patch(`/components/${id}/`, data);
    return response.data;
  },

  addCrossReference: async (id: string, componentId: string): Promise<any> => {
    const response = await api.post(`/components/${id}/add_cross_reference/`, { component_id: componentId });
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

  lookup: async (id: string): Promise<NexarData> => {
    const response = await api.post(`/components/${id}/lookup/`);
    return response.data;
  },

  uploadImage: async (id: string, formData: FormData): Promise<any> => {
    const response = await api.post(`/components/${id}/upload_image/`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return response.data;
  },

  uploadDatasheet: async (id: string, formData: FormData): Promise<any> => {
    const response = await api.post(`/components/${id}/upload_datasheet/`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return response.data;
  },
};

// Component image moderation endpoints
export const componentImages = {
  list: async (params?: any): Promise<PaginatedResponse<any>> => {
    const response = await api.get('/component-images/', { params });
    return response.data;
  },

  approve: async (id: string): Promise<{ detail: string }> => {
    const response = await api.post(`/component-images/${id}/approve/`);
    return response.data;
  },

  reject: async (id: string): Promise<void> => {
    await api.post(`/component-images/${id}/reject/`);
  },
};

// Component datasheet moderation endpoints
export const componentDatasheets = {
  list: async (params?: any): Promise<PaginatedResponse<any>> => {
    const response = await api.get('/component-datasheets/', { params });
    return response.data;
  },

  approve: async (id: string): Promise<{ detail: string }> => {
    const response = await api.post(`/component-datasheets/${id}/approve/`);
    return response.data;
  },

  reject: async (id: string): Promise<void> => {
    await api.post(`/component-datasheets/${id}/reject/`);
  },
};

// Product-component voting endpoints
export const productComponents = {
  vote: async (pcId: string, voteType: 'confirm' | 'dispute'): Promise<ProductComponent> => {
    const response = await api.post(`/product-components/${pcId}/vote/`, { vote_type: voteType });
    return response.data;
  },

  removeVote: async (pcId: string): Promise<ProductComponent> => {
    const response = await api.delete(`/product-components/${pcId}/vote/`);
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

  extractBom: async (id: string): Promise<{
    product: string;
    candidates: BomCandidate[];
    total: number;
    high_confidence: number;
    low_confidence: number;
  }> => {
    const response = await api.get(`/schematics/${id}/extract_bom/`);
    return response.data;
  },

  extractBomOcr: async (id: string): Promise<{
    product: string;
    candidates: BomCandidate[];
    total: number;
    high_confidence: number;
    low_confidence: number;
  }> => {
    const response = await api.get(`/schematics/${id}/extract_bom_ocr/`);
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

  approve: async (id: string): Promise<{ detail: string }> => {
    const response = await api.post(`/schematics/${id}/approve/`);
    return response.data;
  },

  reject: async (id: string): Promise<void> => {
    await api.post(`/schematics/${id}/reject/`);
  },
};

// Firmware endpoints
export const firmware = {
  list: async (params?: any): Promise<PaginatedResponse<Firmware>> => {
    const response = await api.get('/firmware/', { params });
    return response.data;
  },

  get: async (id: string): Promise<Firmware> => {
    const response = await api.get(`/firmware/${id}/`);
    return response.data;
  },

  download: async (id: string): Promise<{ download_url: string }> => {
    const response = await api.get(`/firmware/${id}/download/`);
    return response.data;
  },

  recent: async (): Promise<Firmware[]> => {
    const response = await api.get('/firmware/recent/');
    return response.data;
  },

  approve: async (id: string): Promise<{ detail: string }> => {
    const response = await api.post(`/firmware/${id}/approve/`);
    return response.data;
  },

  reject: async (id: string): Promise<void> => {
    await api.post(`/firmware/${id}/reject/`);
  },
};

// Component suggestions (machine-extracted BOM candidates) - moderation
export const componentSuggestions = {
  list: async (params?: any): Promise<PaginatedResponse<ComponentSuggestion>> => {
    const response = await api.get('/component-suggestions/', { params });
    return response.data;
  },

  approve: async (id: string): Promise<{ detail: string }> => {
    const response = await api.post(`/component-suggestions/${id}/approve/`);
    return response.data;
  },

  reject: async (id: string): Promise<void> => {
    await api.post(`/component-suggestions/${id}/reject/`);
  },
};

// Product images endpoints (moderation)
export const productImages = {
  list: async (params?: any): Promise<PaginatedResponse<ProductImage>> => {
    const response = await api.get('/product-images/', { params });
    return response.data;
  },

  approve: async (id: string): Promise<{ detail: string }> => {
    const response = await api.post(`/product-images/${id}/approve/`);
    return response.data;
  },

  reject: async (id: string): Promise<void> => {
    await api.post(`/product-images/${id}/reject/`);
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
      users: r.users?.results || r.users || [],
    };
  },
};

// Stats endpoint
export const stats = {
  get: async (): Promise<{
    products: number;
    components: number;
    schematics: number;
    firmware: number;
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

  myReports: async (params?: any): Promise<PaginatedResponse<Report>> => {
    const response = await api.get('/reports/my_reports/', { params });
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

// Users endpoints
export const users = {
  list: async (params?: Record<string, any>): Promise<PaginatedResponse<PublicUser>> => {
    const response = await api.get('/users/', { params });
    return response.data;
  },

  get: async (id: string): Promise<PublicUser> => {
    const response = await api.get(`/users/${id}/`);
    return response.data;
  },

  search: async (query: string): Promise<PaginatedResponse<PublicUser>> => {
    const response = await api.get('/users/', { params: { search: query } });
    return response.data;
  },

  stats: async (id: string): Promise<UserStats> => {
    const response = await api.get(`/users/${id}/stats/`);
    return response.data;
  },

  contributions: async (id: string): Promise<UserContributions> => {
    const response = await api.get(`/users/${id}/contributions/`);
    return response.data;
  },
};

// Messaging endpoints
export const messaging = {
  conversations: async (params?: any): Promise<PaginatedResponse<Conversation>> => {
    const response = await api.get('/conversations/', { params });
    return response.data;
  },

  conversation: async (id: string): Promise<Conversation> => {
    const response = await api.get(`/conversations/${id}/`);
    return response.data;
  },

  messages: async (conversationId: string, params?: any): Promise<PaginatedResponse<Message>> => {
    const response = await api.get(`/conversations/${conversationId}/messages/`, { params });
    return response.data;
  },

  send: async (data: { conversation_id?: string; recipient_id?: string; content: string; files?: File[] }): Promise<Message> => {
    if (data.files && data.files.length > 0) {
      const form = new FormData();
      if (data.content) form.append('content', data.content);
      if (data.conversation_id) form.append('conversation_id', data.conversation_id);
      if (data.recipient_id) form.append('recipient_id', data.recipient_id);
      data.files.forEach((f) => form.append('files', f));
      const response = await api.post('/messages/send/', form, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });
      return response.data;
    }
    const response = await api.post('/messages/send/', data);
    return response.data;
  },

  unreadCount: async (): Promise<{ unread_count: number }> => {
    const response = await api.get('/messages/unread-count/');
    return response.data;
  },

  blocks: async (): Promise<PaginatedResponse<UserBlock>> => {
    const response = await api.get('/messages/blocks/');
    return response.data;
  },

  blockUser: async (userId: string): Promise<UserBlock> => {
    const response = await api.post('/messages/blocks/', { user_id: userId });
    return response.data;
  },

  unblockUser: async (blockId: string): Promise<void> => {
    await api.delete(`/messages/blocks/${blockId}/`);
  },
};

// Notifications endpoints
export const notifications = {
  list: async (params?: any): Promise<PaginatedResponse<AppNotification>> => {
    const response = await api.get('/notifications/', { params });
    return response.data;
  },

  unreadCount: async (): Promise<{ count: number }> => {
    const response = await api.get('/notifications/unread-count/');
    return response.data;
  },

  markRead: async (id: string): Promise<AppNotification> => {
    const response = await api.post(`/notifications/${id}/mark-read/`);
    return response.data;
  },

  markAllRead: async (): Promise<{ updated: number }> => {
    const response = await api.post('/notifications/mark-all-read/');
    return response.data;
  },

  vapidPublicKey: async (): Promise<{ key: string }> => {
    const response = await api.get('/notifications/vapid-public-key/');
    return response.data;
  },

  pushSubscribe: async (subscription: PushSubscriptionJSON): Promise<void> => {
    await api.post('/notifications/push-subscribe/', subscription);
  },

  pushUnsubscribe: async (endpoint: string): Promise<void> => {
    await api.post('/notifications/push-unsubscribe/', { endpoint });
  },
};

// Junkbin endpoints
export const junkbin = {
  myItems: async (params?: Record<string, any>): Promise<PaginatedResponse<JunkbinItem>> => {
    const response = await api.get('/junkbin/my_items/', { params });
    return response.data;
  },

  mySummary: async (): Promise<JunkbinSummary> => {
    const response = await api.get('/junkbin/my_summary/');
    return response.data;
  },

  userSummary: async (userId: string): Promise<{ have_count: number; available_count: number }> => {
    const response = await api.get('/junkbin/user_summary/', { params: { user: userId } });
    return response.data;
  },

  check: async (contentType: string, objectId: string): Promise<JunkbinCheckResponse> => {
    const response = await api.get('/junkbin/check/', {
      params: { content_type: contentType, object_id: objectId },
    });
    return response.data;
  },

  create: async (data: {
    content_type: string;
    object_id: string;
    item_type: string;
    status?: string;
    condition?: string;
    visibility?: string;
    notes?: string;
    quantity?: number;
  }): Promise<JunkbinItem> => {
    const response = await api.post('/junkbin/', data);
    return response.data;
  },

  update: async (id: string, data: Partial<JunkbinItem>): Promise<JunkbinItem> => {
    const response = await api.patch(`/junkbin/${id}/`, data);
    return response.data;
  },

  delete: async (id: string): Promise<void> => {
    await api.delete(`/junkbin/${id}/`);
  },

  list: async (params?: Record<string, any>): Promise<PaginatedResponse<JunkbinItem>> => {
    const response = await api.get('/junkbin/', { params });
    return response.data;
  },
};

// Recipes endpoints
export const recipes = {
  list: async (params?: Record<string, any>): Promise<PaginatedResponse<Recipe>> => {
    const response = await api.get('/recipes/', { params });
    return response.data;
  },

  get: async (id: string): Promise<Recipe> => {
    const response = await api.get(`/recipes/${id}/`);
    return response.data;
  },

  create: async (formData: FormData): Promise<Recipe> => {
    const response = await api.post('/recipes/', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return response.data;
  },

  update: async (id: string, formData: FormData): Promise<Recipe> => {
    const response = await api.patch(`/recipes/${id}/`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return response.data;
  },

  delete: async (id: string): Promise<void> => {
    await api.delete(`/recipes/${id}/`);
  },

  buildable: async (params?: Record<string, any>): Promise<PaginatedResponse<Recipe>> => {
    const response = await api.get('/recipes/buildable/', { params });
    return response.data;
  },

  match: async (id: string): Promise<RecipeMatchDetail> => {
    const response = await api.get(`/recipes/${id}/match/`);
    return response.data;
  },

  categories: async (): Promise<Array<{ value: string; label: string; count: number }>> => {
    const response = await api.get('/recipes/categories/');
    return response.data;
  },

  approve: async (id: string): Promise<{ detail: string }> => {
    const response = await api.post(`/recipes/${id}/approve/`);
    return response.data;
  },

  reject: async (id: string): Promise<void> => {
    await api.post(`/recipes/${id}/reject/`);
  },
};

// Analytics endpoints (staff-only)
export const analytics = {
  dashboard: async (days: number = 30): Promise<AnalyticsDashboardData> => {
    const response = await api.get('/analytics/', { params: { days } });
    return response.data;
  },
};

// Newsletter endpoint
export const newsletter = {
  subscribe: async (email: string, source: string = 'landing'): Promise<{ message: string; email: string }> => {
    const response = await api.post('/newsletter/subscribe/', { email, source });
    return response.data;
  },
  unsubscribe: async (token: string): Promise<{ message: string; email: string }> => {
    const response = await api.get(`/newsletter/unsubscribe/${token}/`);
    return response.data;
  },
};

// Self-hosted background removal preview (apps.media_tools)
export const bgRemoval = {
  create: async (file: File, params?: BackgroundRemovalParams): Promise<BackgroundRemovalPreview> => {
    const formData = new FormData();
    formData.append('original', file);
    if (params?.model_name) formData.append('model_name', params.model_name);
    if (params?.alpha_matting !== undefined) formData.append('alpha_matting', String(params.alpha_matting));
    if (params?.foreground_threshold !== undefined) formData.append('foreground_threshold', String(params.foreground_threshold));
    if (params?.background_threshold !== undefined) formData.append('background_threshold', String(params.background_threshold));
    if (params?.erode_size !== undefined) formData.append('erode_size', String(params.erode_size));
    const response = await api.post('/bg-removal/', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return response.data;
  },

  get: async (id: string): Promise<BackgroundRemovalPreview> => {
    const response = await api.get(`/bg-removal/${id}/`);
    return response.data;
  },

  reprocess: async (id: string, params: BackgroundRemovalParams): Promise<BackgroundRemovalPreview> => {
    const response = await api.post(`/bg-removal/${id}/reprocess/`, params);
    return response.data;
  },

  // Retroactive moderator flow - creates a preview from an already-saved
  // image (no re-upload) instead of a fresh file.
  createFromExisting: async (
    source: { productImageId: string } | { componentImageId: string }
  ): Promise<BackgroundRemovalPreview> => {
    const payload = 'productImageId' in source
      ? { product_image: source.productImageId }
      : { component_image: source.componentImageId };
    const response = await api.post('/bg-removal/', payload);
    return response.data;
  },

  // Finds the applied preview for an already-processed image, so it can
  // be reverted without denormalizing a pointer onto the image itself.
  findApplied: async (
    source: { productImageId: string } | { componentImageId: string }
  ): Promise<BackgroundRemovalPreview | null> => {
    const params = 'productImageId' in source
      ? { product_image: source.productImageId }
      : { component_image: source.componentImageId };
    const response = await api.get('/bg-removal/', { params });
    const applied = (response.data.results || response.data).find(
      (p: BackgroundRemovalPreview) => !!p.applied_at
    );
    return applied || null;
  },

  apply: async (id: string): Promise<ProductImage | ComponentImage> => {
    const response = await api.post(`/bg-removal/${id}/apply/`);
    return response.data;
  },

  revert: async (id: string): Promise<ProductImage | ComponentImage> => {
    const response = await api.post(`/bg-removal/${id}/revert/`);
    return response.data;
  },
};
