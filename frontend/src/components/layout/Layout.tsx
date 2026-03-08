import { useState } from 'react';
import { Outlet } from 'react-router-dom';
import Header from './Header';
import Footer from './Footer';
import BackToTop from '../BackToTop';
import OnboardingTips from '../OnboardingTips';
import KeyboardShortcutsModal from '../KeyboardShortcutsModal';
import DontShitYourPants from '../DontShitYourPants';
import useKeyboardShortcuts from '../../hooks/useKeyboardShortcuts';
import { useKonamiCode } from '../../hooks/useKonamiCode';

export default function Layout() {
  const [showShortcuts, setShowShortcuts] = useState(false);
  const [showGame, setShowGame] = useState(false);

  useKeyboardShortcuts(() => setShowShortcuts(true));
  useKonamiCode(() => setShowGame(true));

  return (
    <div className="min-h-screen flex flex-col">
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
    </div>
  );
}
