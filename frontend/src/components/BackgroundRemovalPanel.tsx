import { useEffect, useRef, useState } from 'react';
import { Loader2, RotateCcw, Sparkles, ChevronDown, AlertCircle, Check, X } from 'lucide-react';
import clsx from 'clsx';
import { bgRemoval } from '../api/endpoints';
import { MODEL_OPTIONS } from '../constants/bgRemoval';

export interface BgRemovalState {
  id: string;
  status: 'pending' | 'done' | 'failed';
  resultUrl: string | null;
  error: string | null;
  useProcessed: boolean;
  modelName: string;
  alphaMatting: boolean;
  foregroundThreshold: number;
  backgroundThreshold: number;
  erodeSize: number;
}

export const DEFAULT_BG_REMOVAL_PARAMS = {
  modelName: 'u2net',
  alphaMatting: false,
  foregroundThreshold: 240,
  backgroundThreshold: 10,
  erodeSize: 10,
};

interface BackgroundRemovalPanelProps {
  originalPreviewUrl: string;
  state: BgRemovalState;
  onChange: (updates: Partial<BgRemovalState>) => void;
  /** 'select' (default): Use Processed / Keep Original toggle - decides
   * which version gets uploaded, nothing touches the server yet.
   * 'apply': Apply to Live Image / Discard - this preview is already
   * linked to an existing, published image (the retroactive moderator
   * flow), so the decision here is a real, immediate server mutation. */
  mode?: 'select' | 'apply';
  onApply?: () => void;
  onDiscard?: () => void;
  applying?: boolean;
}

export default function BackgroundRemovalPanel({
  originalPreviewUrl, state, onChange, mode = 'select', onApply, onDiscard, applying,
}: BackgroundRemovalPanelProps) {
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [sliderPct, setSliderPct] = useState(50);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    if (state.status !== 'pending' || !state.id) return;

    pollRef.current = setInterval(async () => {
      try {
        const updated = await bgRemoval.get(state.id);
        if (updated.status !== 'pending') {
          onChange({
            status: updated.status,
            resultUrl: updated.result,
            error: updated.error || null,
          });
        }
      } catch {
        onChange({ status: 'failed', error: 'Lost connection while processing.' });
      }
    }, 1500);

    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [state.status, state.id]);

  const handleReprocess = async () => {
    onChange({ status: 'pending', error: null });
    try {
      await bgRemoval.reprocess(state.id, {
        model_name: state.modelName,
        alpha_matting: state.alphaMatting,
        foreground_threshold: state.foregroundThreshold,
        background_threshold: state.backgroundThreshold,
        erode_size: state.erodeSize,
      });
    } catch {
      onChange({ status: 'failed', error: 'Could not start reprocessing.' });
    }
  };

  if (state.status === 'pending') {
    return (
      <div className="flex items-center gap-2 text-xs font-mono text-cyber-cyan py-2">
        <Loader2 className="h-3.5 w-3.5 animate-spin" />
        Removing background{state.alphaMatting ? ' (refining edges, this takes longer)' : ''}...
      </div>
    );
  }

  if (state.status === 'failed') {
    return (
      <div className="flex items-start gap-2 text-xs font-mono text-cyber-pink py-2">
        <AlertCircle className="h-3.5 w-3.5 shrink-0 mt-0.5" />
        <span>
          {state.error || 'Background removal failed.'}{' '}
          {mode === 'select' ? 'Original photo will be used.' : 'Nothing was changed.'}
        </span>
      </div>
    );
  }

  // status === 'done'
  return (
    <div className="space-y-2 border-t border-cyber-light/20 pt-2 mt-2">
      {/* Before/after compare slider */}
      <div
        className="relative aspect-video bg-cyber-black overflow-hidden select-none"
        onMouseMove={(e) => {
          if (e.buttons !== 1) return;
          const rect = e.currentTarget.getBoundingClientRect();
          setSliderPct(Math.min(100, Math.max(0, ((e.clientX - rect.left) / rect.width) * 100)));
        }}
      >
        <img src={originalPreviewUrl} alt="Original" className="absolute inset-0 w-full h-full object-contain" />
        <div
          className="absolute inset-0 overflow-hidden"
          style={{ clipPath: `inset(0 ${100 - sliderPct}% 0 0)` }}
        >
          <img src={state.resultUrl || ''} alt="Background removed" className="absolute inset-0 w-full h-full object-contain" />
        </div>
        <div
          className="absolute inset-y-0 w-0.5 bg-cyber-cyan pointer-events-none"
          style={{ left: `${sliderPct}%` }}
        />
        <input
          type="range"
          min={0}
          max={100}
          value={sliderPct}
          onChange={(e) => setSliderPct(Number(e.target.value))}
          className="absolute inset-x-0 bottom-1 w-[calc(100%-1rem)] mx-2 accent-cyber-cyan"
        />
        <span className="absolute top-1 left-1 text-[10px] font-mono bg-cyber-black/70 text-gray-300 px-1">PROCESSED</span>
        <span className="absolute top-1 right-1 text-[10px] font-mono bg-cyber-black/70 text-gray-300 px-1">ORIGINAL</span>
      </div>

      {mode === 'select' ? (
        <div className="flex gap-2">
          <button
            type="button"
            onClick={() => onChange({ useProcessed: true })}
            className={clsx(
              'flex-1 text-xs font-mono py-1.5 border transition-colors',
              state.useProcessed
                ? 'border-cyber-cyan text-cyber-cyan bg-cyber-cyan/10'
                : 'border-cyber-light/40 text-gray-500 hover:text-white'
            )}
          >
            Use Processed
          </button>
          <button
            type="button"
            onClick={() => onChange({ useProcessed: false })}
            className={clsx(
              'flex-1 flex items-center justify-center gap-1 text-xs font-mono py-1.5 border transition-colors',
              !state.useProcessed
                ? 'border-cyber-yellow text-cyber-yellow bg-cyber-yellow/10'
                : 'border-cyber-light/40 text-gray-500 hover:text-white'
            )}
          >
            <RotateCcw className="h-3 w-3" />
            Keep Original
          </button>
        </div>
      ) : (
        <div className="flex gap-2">
          <button
            type="button"
            onClick={onApply}
            disabled={applying}
            className="flex-1 flex items-center justify-center gap-1 text-xs font-mono py-1.5 border border-cyber-green/50 text-cyber-green hover:bg-cyber-green/10 transition-colors disabled:opacity-50"
          >
            {applying ? <Loader2 className="h-3 w-3 animate-spin" /> : <Check className="h-3 w-3" />}
            Apply to Live Image
          </button>
          <button
            type="button"
            onClick={onDiscard}
            disabled={applying}
            className="flex-1 flex items-center justify-center gap-1 text-xs font-mono py-1.5 border border-cyber-light/40 text-gray-500 hover:text-white transition-colors disabled:opacity-50"
          >
            <X className="h-3 w-3" />
            Discard
          </button>
        </div>
      )}

      {/* Advanced controls */}
      <div>
        <button
          type="button"
          onClick={() => setShowAdvanced((v) => !v)}
          className="flex items-center gap-1 text-[11px] font-mono text-gray-500 hover:text-cyber-cyan transition-colors"
        >
          <ChevronDown className={clsx('h-3 w-3 transition-transform', showAdvanced && 'rotate-180')} />
          Advanced
        </button>

        {showAdvanced && (
          <div className="mt-2 space-y-2 border border-cyber-light/20 bg-cyber-dark/50 p-2">
            <div>
              <label className="block text-[10px] font-mono text-gray-500 mb-1">Model</label>
              <select
                value={state.modelName}
                onChange={(e) => onChange({ modelName: e.target.value })}
                className="input-cyber text-xs py-1 w-full"
              >
                {MODEL_OPTIONS.map((m) => (
                  <option key={m.value} value={m.value}>{m.label}</option>
                ))}
              </select>
            </div>

            <label className="flex items-center gap-2 text-[11px] font-mono text-gray-400">
              <input
                type="checkbox"
                checked={state.alphaMatting}
                onChange={(e) => onChange({ alphaMatting: e.target.checked })}
                className="accent-cyber-cyan"
              />
              Refine edges (slower, not always better)
            </label>

            {state.alphaMatting && (
              <div className="space-y-2 pl-1">
                <div>
                  <label className="block text-[10px] font-mono text-gray-500 mb-0.5">
                    Foreground threshold ({state.foregroundThreshold})
                  </label>
                  <input
                    type="range" min={0} max={255}
                    value={state.foregroundThreshold}
                    onChange={(e) => onChange({ foregroundThreshold: Number(e.target.value) })}
                    className="w-full accent-cyber-cyan"
                  />
                </div>
                <div>
                  <label className="block text-[10px] font-mono text-gray-500 mb-0.5">
                    Background threshold ({state.backgroundThreshold})
                  </label>
                  <input
                    type="range" min={0} max={255}
                    value={state.backgroundThreshold}
                    onChange={(e) => onChange({ backgroundThreshold: Number(e.target.value) })}
                    className="w-full accent-cyber-cyan"
                  />
                </div>
                <div>
                  <label className="block text-[10px] font-mono text-gray-500 mb-0.5">
                    Erode size ({state.erodeSize})
                  </label>
                  <input
                    type="range" min={0} max={40}
                    value={state.erodeSize}
                    onChange={(e) => onChange({ erodeSize: Number(e.target.value) })}
                    className="w-full accent-cyber-cyan"
                  />
                </div>
              </div>
            )}

            <button
              type="button"
              onClick={handleReprocess}
              className="w-full flex items-center justify-center gap-1.5 text-xs font-mono py-1.5 border border-cyber-green/50 text-cyber-green hover:bg-cyber-green/10 transition-colors"
            >
              <Sparkles className="h-3.5 w-3.5" />
              Reprocess
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
