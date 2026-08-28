import { useState } from 'react';
import { Sparkles, RotateCcw, Loader2 } from 'lucide-react';
import { bgRemoval } from '../api/endpoints';
import { useAuth } from '../context/AuthContext';
import { BG_REMOVAL_ELIGIBLE_IMAGE_TYPES } from '../constants/bgRemoval';
import BackgroundRemovalPanel, { BgRemovalState, DEFAULT_BG_REMOVAL_PARAMS } from './BackgroundRemovalPanel';

interface EligibleImage {
  id?: string;
  image: string;
  image_type?: string;
  background_removed?: boolean;
  has_transparency?: boolean;
}

interface RetroactiveBgRemovalProps {
  image: EligibleImage;
  kind: 'product' | 'component';
  onApplied: () => void;
}

/**
 * Moderator-only control for running background removal on an image that
 * was already uploaded before this feature existed (or that the uploader
 * didn't have it auto-applied to). Hidden entirely unless the viewer is a
 * moderator/staff and the image is actually eligible - already-processed
 * and already-transparent images are excluded automatically, both here
 * and again server-side in case this ever gets called some other way.
 */
export default function RetroactiveBgRemoval({ image, kind, onApplied }: RetroactiveBgRemovalProps) {
  const { user } = useAuth();
  const [isOpen, setIsOpen] = useState(false);
  const [applying, setApplying] = useState(false);
  const [undoing, setUndoing] = useState(false);
  const [state, setState] = useState<BgRemovalState | null>(null);

  const isModerator = !!(user?.is_moderator || user?.is_staff);
  const inScope = !!image.id && !!image.image_type && BG_REMOVAL_ELIGIBLE_IMAGE_TYPES.includes(image.image_type);
  const eligibleToRun = inScope && !image.background_removed && !image.has_transparency;

  if (!isModerator || !inScope) return null;

  const handleUndo = async () => {
    setUndoing(true);
    try {
      const source = kind === 'product' ? { productImageId: image.id! } : { componentImageId: image.id! };
      const applied = await bgRemoval.findApplied(source);
      if (applied) {
        await bgRemoval.revert(applied.id);
        onApplied();
      }
    } finally {
      setUndoing(false);
    }
  };

  if (!eligibleToRun) {
    if (!image.background_removed) return null; // e.g. already-transparent - nothing to offer
    return (
      <button
        type="button"
        onClick={handleUndo}
        disabled={undoing}
        className="flex items-center gap-1 text-[11px] font-mono text-gray-500 hover:text-cyber-yellow transition-colors disabled:opacity-50"
        title="Moderator tool: restore this image to before background removal"
      >
        {undoing ? <Loader2 className="h-3 w-3 animate-spin" /> : <RotateCcw className="h-3 w-3" />}
        Undo Background Removal
      </button>
    );
  }

  const start = async () => {
    setIsOpen(true);
    setState({
      id: '', status: 'pending', resultUrl: null, error: null, useProcessed: true,
      ...DEFAULT_BG_REMOVAL_PARAMS,
    });
    try {
      const preview = await bgRemoval.createFromExisting(
        kind === 'product' ? { productImageId: image.id! } : { componentImageId: image.id! }
      );
      setState((prev) => (prev ? { ...prev, id: preview.id } : prev));
    } catch {
      setState((prev) => (prev ? { ...prev, status: 'failed', error: 'Could not start background removal.' } : prev));
    }
  };

  const handleApply = async () => {
    if (!state?.id) return;
    setApplying(true);
    try {
      await bgRemoval.apply(state.id);
      setIsOpen(false);
      setState(null);
      onApplied();
    } catch {
      setState((prev) => (prev ? { ...prev, error: 'Could not apply — try again.' } : prev));
    } finally {
      setApplying(false);
    }
  };

  const handleDiscard = () => {
    setIsOpen(false);
    setState(null);
  };

  if (!isOpen) {
    return (
      <button
        type="button"
        onClick={start}
        className="flex items-center gap-1 text-[11px] font-mono text-gray-500 hover:text-cyber-cyan transition-colors"
        title="Moderator tool: run background removal on this existing image"
      >
        <Sparkles className="h-3 w-3" />
        Remove Background
      </button>
    );
  }

  if (!state) return null;

  return (
    <div className="mt-2">
      <BackgroundRemovalPanel
        originalPreviewUrl={image.image}
        state={state}
        onChange={(updates) => setState((prev) => (prev ? { ...prev, ...updates } : prev))}
        mode="apply"
        onApply={handleApply}
        onDiscard={handleDiscard}
        applying={applying}
      />
    </div>
  );
}
