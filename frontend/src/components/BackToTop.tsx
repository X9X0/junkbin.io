import { useState, useEffect } from 'react';
import { ChevronUp } from 'lucide-react';
import clsx from 'clsx';

export default function BackToTop() {
  const [isVisible, setIsVisible] = useState(false);

  useEffect(() => {
    const toggleVisibility = () => {
      // Show button when page is scrolled down 400px
      setIsVisible(window.scrollY > 400);
    };

    window.addEventListener('scroll', toggleVisibility, { passive: true });
    return () => window.removeEventListener('scroll', toggleVisibility);
  }, []);

  const scrollToTop = () => {
    window.scrollTo({
      top: 0,
      behavior: 'smooth',
    });
  };

  return (
    <button
      onClick={scrollToTop}
      className={clsx(
        'fixed bottom-6 right-6 z-40 p-3',
        'bg-cyber-dark/90 border border-cyber-cyan/50',
        'text-cyber-cyan hover:bg-cyber-cyan/20 hover:border-cyber-cyan',
        'transition-all duration-300',
        'shadow-lg shadow-cyber-cyan/20',
        isVisible
          ? 'opacity-100 translate-y-0'
          : 'opacity-0 translate-y-4 pointer-events-none'
      )}
      aria-label="Back to top"
    >
      <ChevronUp className="h-5 w-5" />
    </button>
  );
}
