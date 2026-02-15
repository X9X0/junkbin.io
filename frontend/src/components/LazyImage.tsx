import { useState } from 'react';
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

  if (hasError && fallback) {
    return <>{fallback}</>;
  }

  return (
    <img
      src={src}
      alt={alt}
      loading="lazy"
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
