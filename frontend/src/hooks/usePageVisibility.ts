import { useState, useEffect } from 'react';

export function usePageVisibility(): boolean {
  const [isVisible, setIsVisible] = useState(!document.hidden);

  useEffect(() => {
    const handleChange = () => setIsVisible(!document.hidden);
    document.addEventListener('visibilitychange', handleChange);
    return () => document.removeEventListener('visibilitychange', handleChange);
  }, []);

  return isVisible;
}
