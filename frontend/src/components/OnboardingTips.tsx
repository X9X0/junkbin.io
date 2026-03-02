import { useState, useEffect } from 'react';
import { X, Lightbulb, ChevronRight, ChevronLeft } from 'lucide-react';
import clsx from 'clsx';
import { useTranslation } from 'react-i18next';

interface Tip {
  id: string;
  title: string;
  description: string;
  page?: string; // If set, only show on this page
}

const TIPS: Tip[] = [
  {
    id: 'welcome',
    title: 'Welcome to Junkbin!',
    description: 'This is a community database for electronic components and repair documentation. Start by browsing products or searching for a specific part.',
  },
  {
    id: 'search',
    title: 'Quick Search',
    description: 'Use the search bar in the header to quickly find products, components, or schematics. Results appear as you type!',
  },
  {
    id: 'cross-reference',
    title: 'Cross-Reference Parts',
    description: 'Click on any component to see which products contain it. Great for finding donor boards for repairs!',
    page: '/components',
  },
  {
    id: 'contribute',
    title: 'Contribute Documentation',
    description: 'Have a device to document? Click "Submit" to add products, upload images, and share schematics with the community.',
  },
  {
    id: 'fcc-lookup',
    title: 'FCC ID Lookup',
    description: 'Products with FCC IDs link directly to the FCC database where you can find official documentation and test reports.',
    page: '/products',
  },
  {
    id: 'export',
    title: 'Export Data',
    description: 'You can export product data as JSON or download a BOM CSV from any product detail page.',
  },
];

const STORAGE_KEY = 'junkbin_onboarding_dismissed';
const TIPS_SEEN_KEY = 'junkbin_tips_seen';

export default function OnboardingTips() {
  const { t } = useTranslation();
  const [isVisible, setIsVisible] = useState(false);
  const [currentTipIndex, setCurrentTipIndex] = useState(0);
  const [seenTips, setSeenTips] = useState<string[]>([]);

  useEffect(() => {
    // Check if user has permanently dismissed tips
    const dismissed = localStorage.getItem(STORAGE_KEY);
    if (dismissed === 'true') return;

    // Load seen tips
    const seen = JSON.parse(localStorage.getItem(TIPS_SEEN_KEY) || '[]');
    setSeenTips(seen);

    // Find first unseen tip
    const unseenIndex = TIPS.findIndex(tip => !seen.includes(tip.id));
    if (unseenIndex !== -1) {
      setCurrentTipIndex(unseenIndex);
      // Delay showing to avoid jarring appearance
      setTimeout(() => setIsVisible(true), 1500);
    }
  }, []);

  const currentTip = TIPS[currentTipIndex];

  const markSeen = (tipId: string) => {
    const newSeen = [...seenTips, tipId];
    setSeenTips(newSeen);
    localStorage.setItem(TIPS_SEEN_KEY, JSON.stringify(newSeen));
  };

  const handleNext = () => {
    markSeen(currentTip.id);
    const nextUnseen = TIPS.findIndex((tip, i) => i > currentTipIndex && !seenTips.includes(tip.id));
    if (nextUnseen !== -1) {
      setCurrentTipIndex(nextUnseen);
    } else {
      setIsVisible(false);
    }
  };

  const handlePrev = () => {
    if (currentTipIndex > 0) {
      setCurrentTipIndex(currentTipIndex - 1);
    }
  };

  const handleDismissAll = () => {
    localStorage.setItem(STORAGE_KEY, 'true');
    setIsVisible(false);
  };

  const handleClose = () => {
    markSeen(currentTip.id);
    setIsVisible(false);
  };

  if (!isVisible || !currentTip) return null;

  const progress = ((seenTips.length + 1) / TIPS.length) * 100;

  return (
    <div className="fixed bottom-4 right-4 z-40 w-80 max-w-[calc(100vw-2rem)]">
      <div className="card-cyber p-4 border-cyber-cyan/50 shadow-lg shadow-cyber-cyan/20">
        {/* Header */}
        <div className="flex items-start justify-between gap-2 mb-3">
          <div className="flex items-center gap-2 text-cyber-cyan">
            <Lightbulb className="h-4 w-4" />
            <span className="font-mono text-xs uppercase tracking-wider">Tip {currentTipIndex + 1}/{TIPS.length}</span>
          </div>
          <button
            onClick={handleClose}
            className="text-gray-500 hover:text-white p-1 -m-1"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        {/* Progress bar */}
        <div className="h-0.5 bg-cyber-light/30 mb-3">
          <div
            className="h-full bg-cyber-cyan transition-all duration-300"
            style={{ width: `${progress}%` }}
          />
        </div>

        {/* Content */}
        <h4 className="font-semibold text-white mb-1">{currentTip.title}</h4>
        <p className="text-sm text-gray-400 mb-4">{currentTip.description}</p>

        {/* Actions */}
        <div className="flex items-center justify-between">
          <button
            onClick={handleDismissAll}
            className="text-xs text-gray-600 hover:text-gray-400"
          >
            {t('onboarding.dismiss')}
          </button>
          <div className="flex items-center gap-2">
            {currentTipIndex > 0 && (
              <button
                onClick={handlePrev}
                className="p-1.5 text-gray-500 hover:text-white border border-cyber-light/50 hover:border-cyber-light"
              >
                <ChevronLeft className="h-4 w-4" />
              </button>
            )}
            <button
              onClick={handleNext}
              className={clsx(
                'px-3 py-1.5 text-xs font-mono flex items-center gap-1',
                'border border-cyber-cyan text-cyber-cyan hover:bg-cyber-cyan/20'
              )}
            >
              {currentTipIndex < TIPS.length - 1 ? (
                <>
                  Next
                  <ChevronRight className="h-3 w-3" />
                </>
              ) : (
                t('onboarding.got_it')
              )}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
