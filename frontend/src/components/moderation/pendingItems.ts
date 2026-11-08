import { Package, FileText, HardDrive, Sparkles, Wrench, ImageIcon, BookOpen } from 'lucide-react';
import { products, schematics, firmware, componentSuggestions, recipes, productImages, componentImages, componentDatasheets } from '../../api/endpoints';
import type { Product, ProductImage, Schematic, Firmware, ComponentSuggestion, Recipe, ComponentDatasheet, ComponentImage } from '../../types';

/** Pending content shared by the moderation table and the review viewer. */
export type PendingItem =
  | { type: 'product'; data: Product }
  | { type: 'schematic'; data: Schematic }
  | { type: 'firmware'; data: Firmware }
  | { type: 'component_suggestion'; data: ComponentSuggestion }
  | { type: 'recipe'; data: Recipe }
  | { type: 'image'; data: ProductImage }
  | { type: 'component_image'; data: ComponentImage & { component: string; uploaded_at: string; uploaded_by?: { id: string; username: string } | null } }
  | { type: 'datasheet'; data: ComponentDatasheet };

export type PendingType = PendingItem['type'];

export const typeBadgeColors: Record<PendingType, string> = {
  product: 'border-cyber-cyan/50 text-cyber-cyan',
  schematic: 'border-cyber-yellow/50 text-cyber-yellow',
  firmware: 'border-purple-400/50 text-purple-400',
  component_suggestion: 'border-cyber-cyan/50 text-cyber-cyan',
  recipe: 'border-cyber-green/50 text-cyber-green',
  image: 'border-cyber-pink/50 text-cyber-pink',
  component_image: 'border-orange-400/50 text-orange-400',
  datasheet: 'border-purple-400/50 text-purple-400',
};

export const typeIcons: Record<PendingType, React.ComponentType<{ className?: string }>> = {
  product: Package,
  schematic: FileText,
  firmware: HardDrive,
  component_suggestion: Sparkles,
  recipe: Wrench,
  image: ImageIcon,
  component_image: ImageIcon,
  datasheet: BookOpen,
};

const moderationApi: Record<PendingType, {
  approve: (id: string) => Promise<unknown>;
  reject: (id: string, notes?: string, reason?: string) => Promise<void>;
  unapprove?: (id: string) => Promise<unknown>;
}> = {
  product: products,
  schematic: schematics,
  firmware,
  component_suggestion: componentSuggestions,
  recipe: recipes,
  image: productImages,
  component_image: componentImages,
  datasheet: componentDatasheets,
};

export const itemKey = (item: PendingItem) => `${item.type}-${item.data.id}`;

export function decide(item: PendingItem, approve: boolean, notes = '', reason = '') {
  const api = moderationApi[item.type];
  return approve ? api.approve(item.data.id!) : api.reject(item.data.id!, notes, reason);
}

/** The preset a rejection's text came from ('Different product'...), if any. */
export function pickedReason(item: PendingItem, notes: string): string {
  return rejectReasons[item.type].find(([, text]) => notes.includes(text))?.[0] ?? '';
}

/** An approved part suggestion has become a BOM entry, and a rejected item is deleted: neither comes back. */
export const canUndoApproval = (type: PendingType) => !!moderationApi[type].unapprove;

export function undoApproval(item: PendingItem) {
  return moderationApi[item.type].unapprove!(item.data.id!);
}

/** A decision made in this review session, newest first in the history. */
export interface Decision { item: PendingItem; approved: boolean; at: number }

export function itemTitle(item: PendingItem): string {
  switch (item.type) {
    case 'product': return `${item.data.manufacturer} ${item.data.model_number}`;
    case 'schematic': return item.data.title;
    case 'firmware': return item.data.title;
    case 'component_suggestion': {
      const cs = item.data;
      return cs.reference_designator ? `${cs.part_number} (${cs.reference_designator})` : cs.part_number || 'Unnamed part';
    }
    case 'image': return item.data.caption || `${item.data.image_type} image`;
    case 'component_image': return item.data.caption || `${item.data.image_type || 'component'} image`;
    case 'datasheet': return item.data.title;
    case 'recipe': return item.data.name;
  }
}

export function itemUser(item: PendingItem): string | null {
  const by = item.type === 'product' || item.type === 'recipe' ? item.data.created_by : item.data.uploaded_by;
  return by?.username || null;
}

export function itemDate(item: PendingItem): string {
  if (item.type === 'product' || item.type === 'recipe') return item.data.created_at;
  return item.data.uploaded_at || '';
}

/** The public page an item belongs to. */
export function itemLink(item: PendingItem): string {
  switch (item.type) {
    case 'product': return `/products/${item.data.id}`;
    case 'recipe': return `/recipes/${item.data.id}`;
    case 'component_image':
    case 'datasheet': return `/components/${item.data.component}/products`;
    default: return `/products/${item.data.product}`;
  }
}

/** The file a moderator should look at, when the item has one. */
export function itemFile(item: PendingItem): { url: string; type: string } | null {
  if (item.type === 'schematic' || item.type === 'datasheet' || item.type === 'firmware') {
    return item.data.file_url ? { url: item.data.file_url, type: item.data.file_type || '' } : null;
  }
  if (item.type === 'image' || item.type === 'component_image') {
    return item.data.image ? { url: item.data.image, type: 'image' } : null;
  }
  return null;
}

export function itemThumbnail(item: PendingItem): string | null {
  if (item.type === 'image' || item.type === 'component_image') return item.data.thumbnail || item.data.image || null;
  if (item.type === 'recipe') return item.data.image || null;
  if (item.type === 'product') return item.data.primary_image?.thumbnail || item.data.primary_image?.image || null;
  return null;
}

const PHOTO_REASONS = [
  ['Wrong category', 'The product is filed under the wrong category (for example an all-in-one PC listed as a laptop), so this photo does not match its listing.'],
  ['Poor BG removal', 'The background removal damaged the product: parts of it are missing or ragged. The photo on a plain background, or with its original background, would be accepted.'],
  ['Different product', 'The photo shows a different product or model.'],
  ['Blurry or small', 'The photo is too blurry or too small to be useful. A sharper, well-lit photo of at least 800 px would be accepted.'],
  ['Watermark or text', 'The photo carries a watermark, logo or overlaid text. Please upload an unmarked photo you took or are allowed to share.'],
  ['Not the whole product', 'The photo shows a part, accessory, box or charger rather than the product itself.'],
  ['Duplicate', 'This photo is already on the page.'],
] as const;

const DOCUMENT_REASONS = [
  ['Wrong product', 'This document is for a different product or board revision. Please upload it on the matching product page.'],
  ['Unreadable', 'The file is unreadable, incomplete or a low-quality scan. A complete, legible copy would be accepted.'],
  ['Wrong type', 'This file is not the document type it was filed as.'],
  ['Duplicate', 'The same document is already on the page.'],
  ['Rights', 'We cannot host this file because of its distribution terms.'],
] as const;

/** One-click starting points for the rejection feedback; the moderator can edit the text. */
export const rejectReasons: Record<PendingType, readonly (readonly [string, string])[]> = {
  image: PHOTO_REASONS,
  component_image: PHOTO_REASONS,
  schematic: DOCUMENT_REASONS,
  datasheet: DOCUMENT_REASONS,
  firmware: [
    ['Wrong product', 'This firmware is for a different product, board revision or chip.'],
    ['Corrupt or empty', 'The dump looks corrupt, empty or erased (all FF or 00). Please re-read the chip and upload a verified dump.'],
    ['Personal data', 'The dump contains personal data such as Wi-Fi passwords, serial numbers or licence keys. Please clear them and upload again.'],
    ['Duplicate', 'The same firmware is already on the page.'],
  ],
  product: [
    ['Already listed', 'This product is already listed. Please add your information to the existing page.'],
    ['Missing details', 'The listing needs the exact maker and model number (as printed on the label) and a category.'],
    ['Not electronics', 'This is not an electronic product we catalogue.'],
    ['Spam', 'This listing looks like advertising or spam.'],
  ],
  recipe: [
    ['Incomplete', 'The recipe needs a parts list and enough steps for someone else to build it.'],
    ['Unsafe', 'The build involves unsafe practices (e.g. mains voltage without isolation) that the write-up does not address.'],
    ['Duplicate', 'A very similar recipe is already published.'],
    ['Spam', 'This looks like advertising or spam.'],
  ],
  component_suggestion: [
    ['Misread part', 'The part number or value was misread from the source.'],
    ['Wrong board', 'This part belongs to a different board or product revision.'],
    ['Duplicate', 'This part is already in the product BOM.'],
  ],
};
