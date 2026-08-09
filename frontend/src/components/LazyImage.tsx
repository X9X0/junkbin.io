import { useState, useRef, useEffect } from 'react';
import clsx from 'clsx';

interface LazyImageProps {
  src: string;
  alt: string;
  className?: string;
  fallback?: React.ReactNode;
}

export default function LazyImage({ src, alt, className, fallback }: LazyImageProps) {
  const [isLoaded, setIsLoaded] = useState(false);
  const [hasError, setHasError] = useState(false);
  const [isVisible, setIsVisible] = useState(false);
  const imgRef = useRef<HTMLImageElement>(null);

  // Native `loading="lazy"` misses images that are already in the viewport
  // when React swaps them in after a skeleton/loading state — the browser's
  // eligibility check runs before the element exists, so it never re-checks
  // once mounted, and the image just never loads until a scroll event. An
  // IntersectionObserver evaluates current position on mount instead.
  useEffect(() => {
    const el = imgRef.current;
    if (!el) return;

    const observer = new IntersectionObserver(
      (entries) => {
        if (entries[0]?.isIntersecting) {
          setIsVisible(true);
          observer.disconnect();
        }
      },
      { rootMargin: '200px' }
    );
    observer.observe(el);
    return () => observer.disconnect();
  }, []);

  if (hasError && fallback) {
    return <>{fallback}</>;
  }

  return (
    <img
      ref={imgRef}
      src={isVisible ? src : undefined}
      alt={alt}
      decoding="async"
      onLoad={() => setIsLoaded(true)}
      onError={() => setHasError(true)}
      className={clsx(
        'bg-cyber-black',
        className,
        'transition-opacity duration-300',
        isLoaded ? 'opacity-100' : 'opacity-0'
      )}
    />
  );
}
