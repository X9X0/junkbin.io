/**
 * Utility for parsing Django REST Framework error responses
 * into user-friendly validation messages.
 */

/** Map of backend field names to human-readable labels */
const FIELD_LABELS: Record<string, string> = {
  // Product fields
  model_number: 'Model Number',
  manufacturer: 'Manufacturer',
  category: 'Category',
  region: 'Region',
  revision: 'Revision',
  year_manufactured: 'Year Manufactured',
  fcc_id: 'FCC ID',
  description: 'Description',
  teardown_notes: 'Teardown Notes',
  // Component fields
  part_number: 'Part Number',
  component_type: 'Component Type',
  package_type: 'Package Type',
  typical_function: 'Typical Function',
  datasheet_url: 'Datasheet URL',
  // User fields
  username: 'Username',
  email: 'Email',
  password: 'Password',
  password_confirm: 'Confirm Password',
  password1: 'Password',
  password2: 'Confirm Password',
  // Recipe fields
  name: 'Name',
  difficulty: 'Difficulty',
  external_url: 'URL',
  estimated_time: 'Estimated Time',
  image: 'Image',
  bom: 'Bill of Materials',
  // Common fields
  non_field_errors: '',
  detail: '',
  // Component linking
  component_id: 'Component',
  reference_designator: 'Reference Designator',
  quantity: 'Quantity',
  location_description: 'Location',
  notes: 'Notes',
  new_component: 'New Component',
  // Messaging
  content: 'Message',
  recipient: 'Recipient',
  subject: 'Subject',
};

/**
 * Convert a backend field name to a user-friendly label.
 * Falls back to title-casing the field name with underscores replaced by spaces.
 */
function getFieldLabel(field: string): string {
  if (field in FIELD_LABELS) return FIELD_LABELS[field];
  return field
    .replace(/_/g, ' ')
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

/**
 * Flatten a single field's error value into a string array.
 * Handles strings, arrays of strings, and nested objects.
 */
function flattenErrors(value: unknown): string[] {
  if (typeof value === 'string') return [value];
  if (Array.isArray(value)) return value.map(String);
  if (typeof value === 'object' && value !== null) {
    // Nested object like { new_component: { part_number: [...] } }
    return Object.entries(value).flatMap(([k, v]) => {
      const label = getFieldLabel(k);
      const msgs = flattenErrors(v);
      return msgs.map((m) => (label ? `${label}: ${m}` : m));
    });
  }
  return [String(value)];
}

/**
 * Parse an Axios error response from DRF into a user-friendly error string.
 *
 * Handles:
 * - { detail: "..." } — single error message
 * - { field: ["msg", ...], ... } — field-level validation errors
 * - { non_field_errors: ["..."] } — non-field errors
 * - string responses
 */
export function parseApiError(err: any, fallback = 'Something went wrong. Please try again.'): string {
  const data = err?.response?.data;
  if (!data) return fallback;

  // String response
  if (typeof data === 'string') return data;

  // Single detail message
  if (data.detail && typeof data.detail === 'string') return data.detail;

  // Field-level errors
  if (typeof data === 'object') {
    const parts: string[] = [];
    for (const [field, value] of Object.entries(data)) {
      if (field === 'duplicate_of') continue; // structured metadata, not a message — see getDuplicateOf()
      const label = getFieldLabel(field);
      const messages = flattenErrors(value);
      if (!label) {
        // non_field_errors or detail — show messages directly
        parts.push(...messages);
      } else {
        parts.push(...messages.map((m) => `${label}: ${m}`));
      }
    }
    return parts.join('. ') || fallback;
  }

  return fallback;
}

export interface DuplicateOf {
  type: 'product' | 'component';
  id: string;
  slug?: string;
  manufacturer: string;
  model_number?: string;
  part_number?: string;
  category_display?: string;
  year_manufactured?: number | null;
  component_type_display?: string;
  package_type?: string;
  description?: string;
  thumbnail?: string | null;
}

/**
 * Extract the "duplicate_of" pointer a create serializer attaches when a
 * submission collides with an existing Product/Component, so the UI can
 * link to the existing entry instead of just showing an error string.
 *
 * Checks both the top level (Product/Component create) and nested under
 * `new_component` (inline component creation via ProductComponentCreateSerializer).
 */
export function getDuplicateOf(err: any): DuplicateOf | null {
  const data = err?.response?.data;
  if (!data || typeof data !== 'object') return null;
  return data.duplicate_of ?? data.new_component?.duplicate_of ?? null;
}
