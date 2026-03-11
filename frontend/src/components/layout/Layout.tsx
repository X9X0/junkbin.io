import { useState, useCallback } from 'react';
import { Outlet } from 'react-router-dom';
import Header from './Header';
import Footer from './Footer';
import BackToTop from '../BackToTop';
import OnboardingTips from '../OnboardingTips';
import KeyboardShortcutsModal from '../KeyboardShortcutsModal';
import DontShitYourPants from '../DontShitYourPants';
import SuspenseFallback from '../SuspenseFallback';
import useKeyboardShortcuts from '../../hooks/useKeyboardShortcuts';
import { useKonamiCode } from '../../hooks/useKonamiCode';

// Throws on render — used to test ErrorBoundary
function ErrorThrower(): never {
  throw new Error('Test error: NO USER SERVICEABLE PARTS INSIDE');
}

export default function Layout() {
  const [showShortcuts, setShowShortcuts] = useState(false);
  const [showGame, setShowGame] = useState(false);
  const [throwError, setThrowError] = useState(false);
  const [showLoading, setShowLoading] = useState(false);

  useKeyboardShortcuts(() => setShowShortcuts(true));
  useKonamiCode(() => setShowGame(true));

  const simulateLoading = useCallback(() => {
    setShowLoading(true);
    setTimeout(() => setShowLoading(false), 2500);
  }, []);

  return (
    <div className="min-h-screen flex flex-col">
      {throwError && <ErrorThrower />}
      {showLoading && (
        <div className="fixed inset-0 z-[200]">
          <SuspenseFallback />
        </div>
      )}
      <Header />
      <main className="flex-1">
        <Outlet />
      </main>
      <Footer />
      <BackToTop />
      <OnboardingTips />
      <KeyboardShortcutsModal
        isOpen={showShortcuts}
        onClose={() => setShowShortcuts(false)}
      />
      <DontShitYourPants
        isOpen={showGame}
        onClose={() => setShowGame(false)}
      />

      {/* Dev-only test buttons */}
      {import.meta.env.VITE_DEV_TOOLS === 'true' && (
        <div className="fixed bottom-4 left-4 z-[150] flex flex-col gap-1.5">
          <button
            onClick={() => setThrowError(true)}
            className="text-[10px] font-mono px-2 py-1 bg-red-950/80 text-red-400 border border-red-800/60 hover:bg-red-900/80 transition-colors"
            title="Trigger ErrorBoundary"
          >
            ⚠ test error
          </button>
          <button
            onClick={simulateLoading}
            className="text-[10px] font-mono px-2 py-1 bg-cyber-dark/80 text-cyber-cyan border border-cyber-cyan/30 hover:bg-cyber-gray/80 transition-colors"
            title="Simulate loading screen (2.5s)"
          >
            ◈ test loading
          </button>
        </div>
      )}
    </div>
  );
}
