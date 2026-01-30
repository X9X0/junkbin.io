import { useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';

interface ShortcutConfig {
  key: string;
  ctrl?: boolean;
  shift?: boolean;
  action: () => void;
  description: string;
}

export const SHORTCUTS: Omit<ShortcutConfig, 'action'>[] = [
  { key: '/', description: 'Focus search' },
  { key: 'g', shift: true, description: 'Go to Products' },
  { key: 'c', shift: true, description: 'Go to Components' },
  { key: 's', shift: true, description: 'Go to Schematics' },
  { key: 'n', shift: true, description: 'New submission' },
  { key: '?', description: 'Show keyboard shortcuts' },
  { key: 'Escape', description: 'Close modal / Clear search' },
];

export default function useKeyboardShortcuts(
  onShowHelp?: () => void
) {
  const navigate = useNavigate();

  const handleKeyDown = useCallback((e: KeyboardEvent) => {
    // Ignore if user is typing in an input
    const target = e.target as HTMLElement;
    if (
      target.tagName === 'INPUT' ||
      target.tagName === 'TEXTAREA' ||
      target.tagName === 'SELECT' ||
      target.isContentEditable
    ) {
      // Allow Escape to blur input
      if (e.key === 'Escape') {
        target.blur();
      }
      return;
    }

    // Focus search with /
    if (e.key === '/' && !e.ctrlKey && !e.shiftKey) {
      e.preventDefault();
      const searchInput = document.querySelector('input[placeholder*="Search"]') as HTMLInputElement;
      searchInput?.focus();
      return;
    }

    // Show help with ?
    if (e.key === '?' && e.shiftKey) {
      e.preventDefault();
      onShowHelp?.();
      return;
    }

    // Navigation shortcuts with Shift
    if (e.shiftKey && !e.ctrlKey && !e.altKey) {
      switch (e.key.toUpperCase()) {
        case 'G':
          e.preventDefault();
          navigate('/products');
          break;
        case 'C':
          e.preventDefault();
          navigate('/components');
          break;
        case 'S':
          e.preventDefault();
          navigate('/schematics');
          break;
        case 'N':
          e.preventDefault();
          navigate('/submit');
          break;
      }
    }
  }, [navigate, onShowHelp]);

  useEffect(() => {
    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [handleKeyDown]);
}
