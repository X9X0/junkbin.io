import { useEffect, useRef, useState, useCallback } from 'react';
import { X, ZoomIn, ZoomOut, ChevronLeft, ChevronRight, RotateCcw } from 'lucide-react';

interface LightboxImage {
  src: string;
  alt?: string;
  caption?: string;
}

interface LightboxProps {
  images: LightboxImage[];
  initialIndex?: number;
  onClose: () => void;
}

export default function Lightbox({ images, initialIndex = 0, onClose }: LightboxProps) {
  const [index, setIndex] = useState(initialIndex);
  const [scale, setScale] = useState(1);
  const [offset, setOffset] = useState({ x: 0, y: 0 });
  const [dragging, setDragging] = useState(false);
  const dragStart = useRef<{ x: number; y: number; ox: number; oy: number } | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  const reset = () => { setScale(1); setOffset({ x: 0, y: 0 }); };
  const goTo = (i: number) => { setIndex(i); reset(); };
  const prev = () => goTo((index - 1 + images.length) % images.length);
  const next = () => goTo((index + 1) % images.length);

  const zoom = useCallback((delta: number) => {
    setScale((s) => {
      const next = Math.min(5, Math.max(1, s + delta));
      if (next <= 1) setOffset({ x: 0, y: 0 });
      return next;
    });
  }, []);

  // Keyboard navigation
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
      else if (e.key === 'ArrowLeft') prev();
      else if (e.key === 'ArrowRight') next();
      else if (e.key === '+' || e.key === '=') zoom(0.5);
      else if (e.key === '-') zoom(-0.5);
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  });

  // Scroll to zoom
  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    const handler = (e: WheelEvent) => {
      e.preventDefault();
      zoom(e.deltaY < 0 ? 0.3 : -0.3);
    };
    el.addEventListener('wheel', handler, { passive: false });
    return () => el.removeEventListener('wheel', handler);
  });

  const onMouseDown = (e: React.MouseEvent) => {
    if (scale <= 1) return;
    e.preventDefault();
    setDragging(true);
    dragStart.current = { x: e.clientX, y: e.clientY, ox: offset.x, oy: offset.y };
  };
  const onMouseMove = (e: React.MouseEvent) => {
    if (!dragging || !dragStart.current) return;
    setOffset({
      x: dragStart.current.ox + (e.clientX - dragStart.current.x),
      y: dragStart.current.oy + (e.clientY - dragStart.current.y),
    });
  };
  const onMouseUp = () => { setDragging(false); dragStart.current = null; };

  const img = images[index];

  return (
    <div
      className="fixed inset-0 z-50 bg-black/95 flex flex-col"
      onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}
    >
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-white/10 flex-shrink-0">
        <span className="text-gray-400 font-mono text-sm">
          {images.length > 1 && <span>{index + 1} / {images.length}</span>}
          {img.caption && <span className="ml-3 text-white">{img.caption}</span>}
        </span>
        <div className="flex items-center gap-2">
          <button onClick={() => zoom(-0.5)} disabled={scale <= 1} className="p-1.5 text-gray-400 hover:text-white disabled:opacity-30 transition-colors" title="Zoom out (-)">
            <ZoomOut className="h-5 w-5" />
          </button>
          <span className="text-gray-500 font-mono text-xs w-10 text-center">{Math.round(scale * 100)}%</span>
          <button onClick={() => zoom(0.5)} disabled={scale >= 5} className="p-1.5 text-gray-400 hover:text-white disabled:opacity-30 transition-colors" title="Zoom in (+)">
            <ZoomIn className="h-5 w-5" />
          </button>
          {scale > 1 && (
            <button onClick={reset} className="p-1.5 text-gray-400 hover:text-white transition-colors" title="Reset (double-click image)">
              <RotateCcw className="h-4 w-4" />
            </button>
          )}
          <button onClick={onClose} className="p-1.5 ml-2 text-gray-400 hover:text-white transition-colors" title="Close (Esc)">
            <X className="h-5 w-5" />
          </button>
        </div>
      </div>

      {/* Image area */}
      <div
        ref={containerRef}
        className="flex-1 overflow-hidden flex items-center justify-center relative select-none"
        style={{ cursor: scale > 1 ? (dragging ? 'grabbing' : 'grab') : 'zoom-in' }}
        onMouseDown={onMouseDown}
        onMouseMove={onMouseMove}
        onMouseUp={onMouseUp}
        onMouseLeave={onMouseUp}
        onDoubleClick={() => scale > 1 ? reset() : zoom(1)}
      >
        <img
          src={img.src}
          alt={img.alt || ''}
          draggable={false}
          style={{
            transform: `scale(${scale}) translate(${offset.x / scale}px, ${offset.y / scale}px)`,
            transition: dragging ? 'none' : 'transform 0.15s ease',
            maxWidth: '90vw',
            maxHeight: 'calc(90vh - 80px)',
            objectFit: 'contain',
          }}
        />
        {scale === 1 && (
          <div className="absolute bottom-4 left-1/2 -translate-x-1/2 text-gray-600 text-xs font-mono pointer-events-none whitespace-nowrap">
            scroll or double-click to zoom · drag to pan
          </div>
        )}
      </div>

      {/* Prev/Next arrows */}
      {images.length > 1 && (
        <>
          <button
            onClick={(e) => { e.stopPropagation(); prev(); }}
            className="absolute left-3 top-1/2 -translate-y-1/2 p-2 bg-black/60 hover:bg-black/80 text-white transition-colors rounded"
          >
            <ChevronLeft className="h-8 w-8" />
          </button>
          <button
            onClick={(e) => { e.stopPropagation(); next(); }}
            className="absolute right-3 top-1/2 -translate-y-1/2 p-2 bg-black/60 hover:bg-black/80 text-white transition-colors rounded"
          >
            <ChevronRight className="h-8 w-8" />
          </button>
        </>
      )}

      {/* Thumbnail strip */}
      {images.length > 1 && (
        <div className="flex gap-2 p-3 border-t border-white/10 overflow-x-auto justify-center flex-shrink-0">
          {images.map((im, i) => (
            <button
              key={i}
              onClick={() => goTo(i)}
              className={`w-16 aspect-[4/3] flex-shrink-0 border-2 overflow-hidden transition-all ${
                i === index ? 'border-cyber-cyan' : 'border-white/20 hover:border-white/50'
              }`}
            >
              <img src={im.src} alt="" className="w-full h-full object-cover" />
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
