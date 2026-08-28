// Kept in sync with MODEL_CHOICES in backend/apps/media_tools/bg_removal.py
export interface ModelOption {
  value: string;
  label: string;
}

export const MODEL_OPTIONS: ModelOption[] = [
  { value: 'isnet-general-use', label: 'General purpose (sharper edges, newer model) (default)' },
  { value: 'u2net', label: 'General purpose (older model)' },
  { value: 'u2netp', label: 'Fast/lightweight (lower quality)' },
];

// Image types where auto background removal makes sense - hero/package
// shots meant to isolate the subject. Matches PRODUCT_IMAGE_TYPES'
// 'overview' and COMPONENT_IMAGE_TYPES' 'package' in ImageUpload.tsx.
export const BG_REMOVAL_ELIGIBLE_IMAGE_TYPES = ['overview', 'package'];
