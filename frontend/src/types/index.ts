// User types
export interface User {
  id: string;
  username: string;
  email: string;
  avatar?: string;
  bio?: string;
  reputation_score: number;
  contribution_count: number;
  is_trusted: boolean;
  is_moderator: boolean;
  created_at: string;
}

// Product types
export interface Product {
  id: string;
  manufacturer: string;
  model_number: string;
  revision?: string;
  region?: string;
  category: string;
  category_display?: string;
  fcc_id?: string;
  ic_id?: string;
  part_number?: string;
  year_manufactured?: number;
  description?: string;
  teardown_notes?: string;
  is_approved: boolean;
  is_featured: boolean;
  component_count: number;
  image_count: number;
  schematic_count: number;
  comment_count?: number;
  created_by?: CreatedBy;
  created_at: string;
  images?: ProductImage[];
  primary_image?: ProductImage;
}

export interface ProductImage {
  id: string;
  image: string;
  thumbnail?: string;
  medium?: string;
  caption?: string;
  image_type: string;
  display_order?: number;
}

export interface CreatedBy {
  id: string;
  username: string;
  avatar?: string;
}

export interface ProductComment {
  id: string;
  author: CreatedBy;
  content: string;
  created_at: string;
  updated_at: string;
}

// Component types
export interface Component {
  id: string;
  part_number: string;
  manufacturer: string;
  component_type: string;
  component_type_display?: string;
  description?: string;
  package_type?: string;
  primary_value?: string;
  datasheet_url?: string;
  usage_count: number;
  is_verified: boolean;
}

export interface ProductComponent {
  id: string;
  product: string;
  component: Component;
  quantity: number;
  designators?: string;
  notes?: string;
  location_description?: string;
  is_verified: boolean;
}

// Schematic types
export interface Schematic {
  id: string;
  product: string;
  schematic_type: string;
  schematic_type_display?: string;
  title: string;
  description?: string;
  version?: string;
  file_url: string;
  file_type: string;
  file_size?: number;
  source_type: string;
  source_type_display?: string;
  source_url?: string;
  download_count: number;
  is_approved: boolean;
  uploaded_by?: CreatedBy;
  uploaded_at: string;
}

// API Response types
export interface PaginatedResponse<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

export interface AuthTokens {
  access: string;
  refresh: string;
}

export interface LoginCredentials {
  username: string;
  password: string;
}

export interface RegisterData {
  username: string;
  email: string;
  password: string;
  password_confirm: string;
}

// Report types
export interface UserMinimal {
  id: string;
  username: string;
  is_trusted: boolean;
  is_moderator: boolean;
}

export interface ReportedItemData {
  type: string;
  id: string;
  display: string;
  manufacturer?: string;
  model_number?: string;
  part_number?: string;
}

export interface Report {
  id: string;
  content_type: string;
  content_type_name: string;
  object_id: string;
  reason: string;
  reason_display: string;
  description: string;
  reporter: UserMinimal;
  reported_user: UserMinimal | null;
  created_at: string;
  status: string;
  status_display: string;
  counted_as_strike: boolean;
  resolved_at: string | null;
  resolved_by: UserMinimal | null;
  resolution_notes: string;
  reported_item_data: ReportedItemData | null;
}

export interface ReportStats {
  total: number;
  pending: number;
  resolved_valid: number;
  resolved_invalid: number;
}

export interface UserReview {
  id: string;
  user: UserMinimal;
  review_type: string;
  review_type_display: string;
  status: string;
  status_display: string;
  trigger_report_count: number;
  triggered_by: Report | null;
  related_reports: Report[];
  created_at: string;
  reviewed_at: string | null;
  reviewer: UserMinimal | null;
  notes: string;
  action_taken: string;
}

// Search/filter types
export interface ProductFilters {
  search?: string;
  category?: string;
  manufacturer?: string;
  has_schematics?: boolean;
  has_components?: boolean;
  ordering?: string;
  page?: number;
}
