import { useState } from 'react';
import { Outlet } from 'react-router-dom';
import Header from './Header';
import Footer from './Footer';
import BackToTop from '../BackToTop';
import OnboardingTips from '../OnboardingTips';
import KeyboardShortcutsModal from '../KeyboardShortcutsModal';
import useKeyboardShortcuts from '../../hooks/useKeyboardShortcuts';

export default function Layout() {
  const [showShortcuts, setShowShortcuts] = useState(false);

  useKeyboardShortcuts(() => setShowShortcuts(true));

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
    </div>
  );
}
