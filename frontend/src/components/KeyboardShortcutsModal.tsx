import { X, Keyboard } from 'lucide-react';
import { SHORTCUTS } from '../hooks/useKeyboardShortcuts';

interface KeyboardShortcutsModalProps {
  isOpen: boolean;
  onClose: () => void;
}

function KeyBadge({ children }: { children: React.ReactNode }) {
  return (
    <span className="inline-flex items-center justify-center min-w-[24px] h-6 px-2 bg-cyber-dark border border-cyber-light/50 text-gray-300 font-mono text-xs rounded">
      {children}
    </span>
  );
}

export default function KeyboardShortcutsModal({ isOpen, onClose }: KeyboardShortcutsModalProps) {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/80 backdrop-blur-sm"
        onClick={onClose}
      />

      {/* Modal */}
      <div className="relative w-full max-w-md card-cyber p-6">
        {/* Close button */}
        <button
          onClick={onClose}
          className="absolute top-4 right-4 text-gray-500 hover:text-white"
        >
          <X className="h-5 w-5" />
        </button>

        {/* Header */}
        <div className="flex items-center gap-3 mb-6">
          <div className="p-2 bg-cyber-cyan/20 border border-cyber-cyan/50">
            <Keyboard className="h-6 w-6 text-cyber-cyan" />
          </div>
          <div>
            <h2 className="font-display text-xl font-bold text-white">
              KEYBOARD SHORTCUTS
            </h2>
            <p className="text-xs text-gray-500 font-mono">Power user navigation</p>
          </div>
        </div>

        {/* Shortcuts list */}
        <div className="space-y-3">
          {SHORTCUTS.map((shortcut, index) => (
            <div
              key={index}
              className="flex items-center justify-between py-2 border-b border-cyber-light/20 last:border-0"
            >
              <span className="text-sm text-gray-300">{shortcut.description}</span>
              <div className="flex items-center gap-1">
                {shortcut.ctrl && (
                  <>
                    <KeyBadge>Ctrl</KeyBadge>
                    <span className="text-gray-600">+</span>
                  </>
                )}
                {shortcut.shift && (
                  <>
                    <KeyBadge>Shift</KeyBadge>
                    <span className="text-gray-600">+</span>
                  </>
                )}
                <KeyBadge>{shortcut.key === '/' ? '/' : shortcut.key.toUpperCase()}</KeyBadge>
              </div>
            </div>
          ))}
        </div>

        {/* Footer */}
        <div className="mt-6 pt-4 border-t border-cyber-light/30 text-center">
          <p className="text-xs text-gray-600">
            Press <KeyBadge>?</KeyBadge> anytime to show this help
          </p>
        </div>
      </div>
    </div>
  );
}
