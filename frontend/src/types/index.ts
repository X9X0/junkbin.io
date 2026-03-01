// Badge types
export interface Badge {
  slug: string;
  name: string;
  description: string;
  icon: string;
  color: string;
  awarded_at: string;
}

// User types
export interface User {
  id: string;
  username: string;
  email: string;
  display_name?: string;
  avatar?: string;
  bio?: string;
  location?: string;
  website?: string;
  reputation_score: number;
  contribution_count: number;
  is_staff: boolean;
  is_trusted: boolean;
  is_moderator: boolean;
  created_at: string;
  badges?: Badge[];
  first_name?: string;
  last_name?: string;
  report_count?: number;
  email_verified?: boolean;
  oauth_provider?: string;
  preferences?: UserPreferences;
  updated_at?: string;
  last_contribution_at?: string;
}

export interface PublicUser {
  id: string;
  username: string;
  display_name?: string;
  avatar?: string;
  bio?: string;
  location?: string;
  website?: string;
  reputation_score: number;
  contribution_count: number;
  is_trusted: boolean;
  created_at: string;
  badges?: Badge[];
}

export interface UserStats {
  total_contributions: number;
  approved_products: number;
  approved_components: number;
  pending_submissions: number;
  reports_submitted: number;
  reports_received: number;
  reputation_rank: number;
}

export interface UserContributions {
  products: Product[];
  components: Component[];
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
  slug?: string;
  subcategory?: string;
  region_display?: string;
  view_count?: number;
  updated_at?: string;
}

export interface ProductImage {
  id: string;
  product?: string;
  image: string;
  thumbnail?: string;
  medium?: string;
  caption?: string;
  image_type: string;
  display_order?: number;
  width?: number;
  height?: number;
  uploaded_by?: { id: string; username: string };
  uploaded_at?: string;
  is_approved: boolean;
}

export interface CreatedBy {
  id: string;
  username: string;
  is_trusted: boolean;
}

export interface ProductComment {
  id: string;
  author: CreatedBy;
  content: string;
  created_at: string;
  updated_at: string;
}

// Component datasheet type
export interface ComponentDatasheet {
  id: string;
  component: string;
  title: string;
  version: string;
  source_type: string;
  source_url: string;
  source_notes: string;
  file_url: string;
  file_type: string;
  file_size: number | null;
  uploaded_by: { id: string; username: string } | null;
  uploaded_at: string;
  is_approved: boolean;
  download_count: number;
}

// Component image type (own image or type-default fallback)
export interface ComponentImage {
  id?: string;
  image: string;
  thumbnail?: string;
  medium?: string;
  image_type?: string;
  caption?: string;
  is_default?: boolean;
  is_approved?: boolean;
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
  typical_function?: string;
  datasheet_url?: string;
  usage_count: number;
  is_verified: boolean;
  pricing_data?: NexarData | null;
  created_by?: CreatedBy;
  primary_image?: ComponentImage | null;
  manufacturer_aliases?: string[];
  specifications?: Record<string, string>;
  octopart_url?: string;
  alternative_part_numbers?: string[];
  cross_references?: Component[];
  images?: ComponentImage[];
  datasheets?: ComponentDatasheet[];
  created_at?: string;
  updated_at?: string;
}

export interface ProductComponent {
  id: string;
  component: Component;
  quantity: number;
  reference_designator?: string;
  notes?: string;
  location_description?: string;
  is_verified: boolean;
  vote_score: number;
  confirm_count: number;
  dispute_count: number;
  needs_review: boolean;
  current_user_vote: 'confirm' | 'dispute' | null;
  created_by?: CreatedBy;
  component_id?: string;
  board_name?: string;
  image_reference?: string;
  submission_level?: string;
  submission_level_display?: string;
  created_at?: string;
}

// Schematic types
export interface Schematic {
  id: string;
  product?: string;
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
  source_notes?: string;
  page_count?: number;
  repair_relevance?: string;
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
  content_type_name?: string;
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
  triggered_by?: Report | null;
  related_reports?: Report[];
  created_at: string;
  reviewed_at: string | null;
  reviewer: UserMinimal | null;
  notes?: string;
  action_taken?: string;
}

// Messaging types
export interface MessageParticipant {
  id: string;
  username: string;
  avatar?: string;
  is_trusted: boolean;
  is_moderator: boolean;
}

export interface MessagePreview {
  content: string;
  sender_id: string | null;
  created_at: string;
  is_read: boolean;
}

export interface Conversation {
  id: string;
  other_participant?: MessageParticipant;
  participant_1?: MessageParticipant;
  participant_2?: MessageParticipant;
  last_message?: MessagePreview | null;
  unread_count?: number;
  created_at?: string;
  updated_at: string;
}

export interface Message {
  id: string;
  sender: MessageParticipant;
  content: string;
  is_read: boolean;
  created_at: string;
  conversation_id?: string;
}

export interface UserBlock {
  id: string;
  blocked_user: MessageParticipant;
  created_at: string;
}

// Junkbin types
export interface JunkbinItem {
  id: string;
  user: { id: string; username: string };
  content_type: 'product' | 'component';
  object_id: string;
  item_name: string;
  item_manufacturer: string;
  item_slug: string | null;
  item_type: 'have' | 'want';
  status: 'available' | 'not_for_trade';
  condition: 'new' | 'working' | 'broken' | 'unknown';
  visibility: 'public' | 'private';
  notes: string;
  quantity: number;
  created_at: string;
  updated_at: string;
}

export interface JunkbinSummary {
  have_count: number;
  want_count: number;
  available_count: number;
}

export interface JunkbinCheckResponse {
  items: JunkbinItem[];
}

// User preferences
export interface UserPreferences {
  email_notifications: boolean;
  notify_messages: boolean;
  notify_submissions: boolean;
  notify_reports: boolean;
  notify_account: boolean;
  notify_junkbin: boolean;
  dark_mode: boolean;
  show_advanced_fields: boolean;
}

// Recipe types
export interface Recipe {
  id: string;
  slug: string;
  name: string;
  description: string;
  difficulty: 'beginner' | 'intermediate' | 'advanced' | 'expert';
  difficulty_display: string;
  category: string;
  category_display: string;
  external_url?: string;
  estimated_time?: string;
  image?: string;
  component_count: number;
  view_count: number;
  build_count?: number;
  is_approved: boolean;
  is_featured: boolean;
  created_by?: CreatedBy;
  created_at: string;
  updated_at?: string;
  bom?: RecipeBomItem[];
  match_percentage?: number | null;
}

export interface RecipeBomItem {
  id: string;
  component_id: string;
  part_number: string;
  manufacturer: string;
  component_type: string;
  component_type_display: string;
  primary_value: string;
  quantity: number;
  notes: string;
  is_optional: boolean;
}

export interface BomMatchItem extends RecipeBomItem {
  user_has: boolean;
  available_from: Array<{
    user_id: string;
    username: string;
    quantity: number;
    condition: string;
  }>;
}

export interface RecipeMatchDetail {
  recipe_id: string;
  recipe_name: string;
  match_percentage: number;
  total_required: number;
  matched_count: number;
  components: BomMatchItem[];
}

// Nexar/Pricing types
export interface SellerOffer {
  stock: number;
  price: number;
  currency: string;
  qty_min: number;
  buy_url: string;
}

export interface Seller {
  name: string;
  url: string;
  offers: SellerOffer[];
}

export interface NexarSpec {
  name: string;
  value: string;
}

export interface NexarData {
  mpn: string;
  manufacturer: string;
  description: string;
  datasheet_url: string | null;
  specs: NexarSpec[];
  sellers: Seller[];
  last_updated: string;
}

// Analytics types
export interface DailyActiveUsers {
  date: string;
  count: number;
}

export interface SearchAnalytics {
  total: number;
  zero_result_pct: number;
  top_queries: Array<{ query: string; count: number }>;
}

export interface TrendingComponent {
  component_id: string;
  component__part_number: string;
  component__manufacturer: string;
  total_views: number;
}

export interface ContentStats {
  products: number;
  components: number;
  schematics: number;
  recipes: number;
}

export interface ActivityBreakdown {
  activity_type: string;
  count: number;
}

export interface AnalyticsDashboardData {
  dau: DailyActiveUsers[];
  search_analytics: SearchAnalytics;
  trending_components: TrendingComponent[];
  content_stats: ContentStats;
  activity_breakdown: ActivityBreakdown[];
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
