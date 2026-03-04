import { useState, useEffect } from 'react';
import {
  BookOpen, Users, Search, Upload, MessageSquare, Package,
  ChevronRight, Menu, X,
  Shield, Star, Heart, Send, Bell, Globe,
} from 'lucide-react';

const WEBLATE_PROJECT = 'https://hosted.weblate.org/projects/junkbin-io';
const GITHUB_REPO = 'https://github.com/X9X0/junkbin.io';

interface Section {
  id: string;
  label: string;
  icon: React.ReactNode;
  color: string;
}

const userSections: Section[] = [
  { id: 'getting-started', label: 'Getting Started', icon: <BookOpen className="h-4 w-4" />, color: 'text-cyber-cyan' },
  { id: 'browsing', label: 'Browsing & Search', icon: <Search className="h-4 w-4" />, color: 'text-cyber-cyan' },
  { id: 'contributing', label: 'Contributing', icon: <Upload className="h-4 w-4" />, color: 'text-cyber-green' },
  { id: 'translations', label: 'Translations', icon: <Globe className="h-4 w-4" />, color: 'text-cyber-green' },
  { id: 'community', label: 'Community', icon: <Users className="h-4 w-4" />, color: 'text-cyber-green' },
  { id: 'junkbin', label: 'Junkbin & Trading', icon: <Package className="h-4 w-4" />, color: 'text-cyber-yellow' },
  { id: 'messaging', label: 'Messaging', icon: <MessageSquare className="h-4 w-4" />, color: 'text-cyber-yellow' },
];

export default function Docs() {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [activeSection, setActiveSection] = useState('getting-started');

  useEffect(() => {
    const handleScroll = () => {
      const sections = userSections;
      for (const section of sections) {
        const el = document.getElementById(section.id);
        if (el) {
          const rect = el.getBoundingClientRect();
          if (rect.top <= 120 && rect.bottom > 120) {
            setActiveSection(section.id);
            break;
          }
        }
      }
    };
    window.addEventListener('scroll', handleScroll, { passive: true });
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  const scrollTo = (id: string) => {
    const el = document.getElementById(id);
    if (el) {
      el.scrollIntoView({ behavior: 'smooth', block: 'start' });
      setSidebarOpen(false);
    }
  };

  return (
    <div className="mx-auto max-w-screen-2xl px-4 py-8">
      {/* Header */}
      <div className="flex items-center gap-3 mb-2">
        <div className="p-2 bg-cyber-cyan/20 border border-cyber-cyan/50">
          <BookOpen className="h-6 w-6 text-cyber-cyan" />
        </div>
        <h1 className="font-display text-2xl font-bold tracking-wider text-white">
          DOCUMENTATION
        </h1>
      </div>
      <p className="text-gray-500 text-sm font-mono mb-8">
        Everything you need to use and contribute to Junkbin.io
      </p>

      {/* Mobile sidebar toggle */}
      <button
        onClick={() => setSidebarOpen(!sidebarOpen)}
        className="lg:hidden flex items-center gap-2 px-3 py-2 mb-4 border border-cyber-light/30 text-gray-400 hover:text-cyber-cyan transition-colors text-sm"
      >
        {sidebarOpen ? <X className="h-4 w-4" /> : <Menu className="h-4 w-4" />}
        {sidebarOpen ? 'Close' : 'Navigation'}
      </button>

      <div className="flex gap-8">
        {/* Sidebar */}
        <nav
          className={`${
            sidebarOpen ? 'block' : 'hidden'
          } lg:block lg:w-56 flex-shrink-0`}
        >
          <div className="lg:sticky lg:top-20 space-y-6">
            <div>
              <h3 className="font-mono text-xs font-semibold text-gray-500 tracking-wider mb-2">
                USER GUIDE
              </h3>
              <ul className="space-y-1">
                {userSections.map((s) => (
                  <li key={s.id}>
                    <button
                      onClick={() => scrollTo(s.id)}
                      className={`flex items-center gap-2 w-full text-left px-2 py-1.5 text-sm transition-colors ${
                        activeSection === s.id
                          ? `${s.color} bg-white/5`
                          : 'text-gray-400 hover:text-white'
                      }`}
                    >
                      {s.icon}
                      {s.label}
                      {activeSection === s.id && (
                        <ChevronRight className="h-3 w-3 ml-auto" />
                      )}
                    </button>
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </nav>

        {/* Content */}
        <div className="flex-1 min-w-0 space-y-8">
          {/* ─── USER GUIDE ─── */}

          {/* Getting Started */}
          <section id="getting-started" className="card-cyber p-6 scroll-mt-20">
            <div className="flex items-center gap-2 mb-4">
              <BookOpen className="h-5 w-5 text-cyber-cyan" />
              <h2 className="font-display text-lg font-bold text-cyber-cyan tracking-wider">
                GETTING STARTED
              </h2>
            </div>

            <div className="space-y-4 text-sm text-gray-300">
              <div>
                <h3 className="text-white font-semibold mb-1">Creating an Account</h3>
                <p className="leading-relaxed">
                  Click <strong className="text-white">Register</strong> in the header to create an account with your
                  email and a password. You'll receive a verification email — click the link to activate your account.
                  Alternatively, sign in instantly with <strong className="text-white">Google</strong> or{' '}
                  <strong className="text-white">GitHub</strong> using the OAuth buttons on the login page.
                </p>
              </div>

              <div>
                <h3 className="text-white font-semibold mb-1">Your Profile</h3>
                <p className="leading-relaxed">
                  Visit <strong className="text-white">Profile</strong> to update your display name, bio, and
                  notification preferences. Your profile page shows your reputation score, badges earned, and
                  contribution history. Other users can view your public profile and junkbin collection.
                </p>
              </div>

              <div>
                <h3 className="text-white font-semibold mb-1">Reputation & Trust</h3>
                <p className="leading-relaxed">
                  Every approved contribution increases your reputation score. At certain thresholds you earn
                  badges like <span className="text-cyber-green">First Contribution</span>,{' '}
                  <span className="text-cyber-green">Prolific Contributor</span>, and{' '}
                  <span className="text-cyber-yellow">Trusted User</span>. Trusted users' submissions are
                  auto-approved without moderator review.
                </p>
              </div>
            </div>
          </section>

          {/* Browsing & Search */}
          <section id="browsing" className="card-cyber p-6 scroll-mt-20">
            <div className="flex items-center gap-2 mb-4">
              <Search className="h-5 w-5 text-cyber-cyan" />
              <h2 className="font-display text-lg font-bold text-cyber-cyan tracking-wider">
                BROWSING & SEARCHING
              </h2>
            </div>

            <div className="space-y-4 text-sm text-gray-300">
              <div>
                <h3 className="text-white font-semibold mb-1">Global Search</h3>
                <p className="leading-relaxed">
                  Use the search bar in the header or press <kbd className="px-1.5 py-0.5 bg-cyber-dark border border-cyber-light/30 text-gray-400 text-xs">/</kbd> to
                  focus it. Results include products, components, schematics, and users — grouped by tab.
                  The search uses PostgreSQL full-text ranking so partial matches and typos still return relevant results.
                </p>
              </div>

              <div>
                <h3 className="text-white font-semibold mb-1">Products</h3>
                <p className="leading-relaxed">
                  Browse the <strong className="text-white">Products</strong> page to see all documented electronics.
                  Filter by manufacturer, category, or region. Switch between grid and list views. Click a product
                  to see its full BOM (bill of materials), schematics, images, and comments.
                </p>
              </div>

              <div>
                <h3 className="text-white font-semibold mb-1">Components</h3>
                <p className="leading-relaxed">
                  The <strong className="text-white">Components</strong> page lists all cataloged parts. Filter by
                  component type (IC, capacitor, resistor, etc.) or package type. Each component page shows which
                  products contain it — the <strong className="text-white">cross-reference</strong> feature that makes
                  Junkbin useful for repair.
                </p>
              </div>

              <div>
                <h3 className="text-white font-semibold mb-1">Keyboard Shortcuts</h3>
                <p className="leading-relaxed">
                  Press <kbd className="px-1.5 py-0.5 bg-cyber-dark border border-cyber-light/30 text-gray-400 text-xs">?</kbd> anywhere
                  to open the keyboard shortcuts modal. Shortcuts include{' '}
                  <kbd className="px-1.5 py-0.5 bg-cyber-dark border border-cyber-light/30 text-gray-400 text-xs">/</kbd> for search,{' '}
                  <kbd className="px-1.5 py-0.5 bg-cyber-dark border border-cyber-light/30 text-gray-400 text-xs">g p</kbd> for products,{' '}
                  <kbd className="px-1.5 py-0.5 bg-cyber-dark border border-cyber-light/30 text-gray-400 text-xs">g c</kbd> for components, and more.
                </p>
              </div>
            </div>
          </section>

          {/* Contributing Content */}
          <section id="contributing" className="card-cyber p-6 scroll-mt-20">
            <div className="flex items-center gap-2 mb-4">
              <Upload className="h-5 w-5 text-cyber-green" />
              <h2 className="font-display text-lg font-bold text-cyber-green tracking-wider">
                CONTRIBUTING CONTENT
              </h2>
            </div>

            <div className="space-y-4 text-sm text-gray-300">
              <div>
                <h3 className="text-white font-semibold mb-1">Submitting a Product</h3>
                <p className="leading-relaxed">
                  Click <strong className="text-white">Contribute</strong> in the header to open the submission wizard.
                  Choose <strong className="text-white">Basic</strong> (manufacturer, model, category, description, image)
                  or <strong className="text-white">Advanced</strong> (adds revision, region, FCC ID, year). Search first
                  to avoid duplicates — if the product exists, add components to it instead.
                </p>
              </div>

              <div>
                <h3 className="text-white font-semibold mb-1">Adding Components</h3>
                <p className="leading-relaxed">
                  From a product's detail page, add components individually or in bulk. The{' '}
                  <strong className="text-white">batch add</strong> form lets you add multiple components at once.
                  For large BOMs, use <strong className="text-white">CSV import</strong> — upload a spreadsheet and
                  map columns using the interactive column mapper. Over 60 column header aliases are recognized
                  automatically.
                </p>
              </div>

              <div>
                <h3 className="text-white font-semibold mb-1">Images & Schematics</h3>
                <p className="leading-relaxed">
                  Upload PCB photos, close-ups, and overview shots from a product's detail page. On mobile, you can
                  capture directly from your camera. Schematics (PDFs, images) can be uploaded to the Schematics tab
                  with source attribution and repair-relevance tags.
                </p>
              </div>

              <div>
                <h3 className="text-white font-semibold mb-1">Recipes</h3>
                <p className="leading-relaxed">
                  Submit a <strong className="text-white">recipe</strong> — a community electronics project with a
                  bill of materials. Use the two-step wizard: fill in project details (name, description, difficulty,
                  category, URL), then build the BOM with component search. Recipes let other users discover what
                  they can build from their junkbin.
                </p>
              </div>
            </div>
          </section>

          {/* Translations */}
          <section id="translations" className="card-cyber p-6 scroll-mt-20">
            <div className="flex items-center gap-2 mb-4">
              <Globe className="h-5 w-5 text-cyber-green" />
              <h2 className="font-display text-lg font-bold text-cyber-green tracking-wider">
                TRANSLATIONS
              </h2>
            </div>

            <div className="space-y-4 text-sm text-gray-300">
              <p className="leading-relaxed">
                Junkbin.io is available in <strong className="text-white">18 languages</strong>. All non-English
                translations are currently machine-translated and need native speaker review. If you speak one of
                these languages, you can improve the quality directly on GitHub — no coding experience needed.
              </p>

              <div>
                <h3 className="text-white font-semibold mb-1">Frontend UI strings (JSON)</h3>
                <p className="leading-relaxed mb-2">
                  All visible text in the app lives in a single JSON file per language. Find your language below,
                  edit the values (not the keys), and open a pull request.
                </p>
                <div className="flex flex-wrap gap-2">
                  {[
                    { code: 'fr', label: 'Français' }, { code: 'es', label: 'Español' },
                    { code: 'pt', label: 'Português' }, { code: 'de', label: 'Deutsch' },
                    { code: 'it', label: 'Italiano' }, { code: 'nl', label: 'Nederlands' },
                    { code: 'pl', label: 'Polski' }, { code: 'cs', label: 'Čeština' },
                    { code: 'sk', label: 'Slovenčina' }, { code: 'hr', label: 'Hrvatski' },
                    { code: 'sr', label: 'Srpski' }, { code: 'sl', label: 'Slovenščina' },
                    { code: 'ru', label: 'Русский' }, { code: 'uk', label: 'Українська' },
                    { code: 'ro', label: 'Română' }, { code: 'hu', label: 'Magyar' },
                    { code: 'tr', label: 'Türkçe' },
                  ].map(({ code, label }) => (
                    <a
                      key={code}
                      href={`${WEBLATE_PROJECT}/frontend-ui/${code}/`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="px-2 py-1 text-xs font-mono border border-cyber-light/30 text-gray-500 hover:text-cyber-cyan hover:border-cyber-cyan/50 transition-colors"
                    >
                      {label}
                    </a>
                  ))}
                </div>
              </div>

              <div>
                <h3 className="text-white font-semibold mb-1">Email templates & error messages (.po files)</h3>
                <p className="leading-relaxed">
                  Backend strings (email subjects, validation errors) use GNU gettext{' '}
                  <code className="px-1 bg-cyber-dark border border-cyber-light/20 text-cyber-cyan text-xs">.po</code>{' '}
                  files. Open your language's file in{' '}
                  <a href="https://poedit.net" target="_blank" rel="noopener noreferrer" className="text-cyber-cyan hover:underline">Poedit</a>{' '}
                  or any text editor, fill in the empty <code className="px-1 bg-cyber-dark border border-cyber-light/20 text-cyber-cyan text-xs">msgstr</code> lines, and submit a PR.
                </p>
              </div>

              <div className="flex gap-3 pt-1">
                <a
                  href={`${WEBLATE_PROJECT}/`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center gap-1.5 text-xs font-mono text-cyber-green border border-cyber-green/40 px-3 py-1.5 hover:bg-cyber-green/10 transition-colors"
                >
                  <Globe className="h-3.5 w-3.5" />
                  Translate on Weblate →
                </a>
              </div>
            </div>
          </section>

          {/* Community Features */}
          <section id="community" className="card-cyber p-6 scroll-mt-20">
            <div className="flex items-center gap-2 mb-4">
              <Users className="h-5 w-5 text-cyber-green" />
              <h2 className="font-display text-lg font-bold text-cyber-green tracking-wider">
                COMMUNITY FEATURES
              </h2>
            </div>

            <div className="space-y-4 text-sm text-gray-300">
              <div className="flex items-start gap-3">
                <Star className="h-4 w-4 text-cyber-yellow flex-shrink-0 mt-0.5" />
                <div>
                  <h3 className="text-white font-semibold mb-1">Voting</h3>
                  <p className="leading-relaxed">
                    Upvote or downvote component entries to help surface accurate information. Votes affect
                    the contributor's reputation.
                  </p>
                </div>
              </div>

              <div className="flex items-start gap-3">
                <MessageSquare className="h-4 w-4 text-cyber-cyan flex-shrink-0 mt-0.5" />
                <div>
                  <h3 className="text-white font-semibold mb-1">Comments</h3>
                  <p className="leading-relaxed">
                    Leave comments on products to share repair tips, corrections, or additional information.
                    Keep comments on-topic and constructive.
                  </p>
                </div>
              </div>

              <div className="flex items-start gap-3">
                <Shield className="h-4 w-4 text-cyber-pink flex-shrink-0 mt-0.5" />
                <div>
                  <h3 className="text-white font-semibold mb-1">Reporting</h3>
                  <p className="leading-relaxed">
                    Report inaccurate information, spam, or guideline violations using the report button on any
                    product, component, or message. Reports are reviewed by moderators. See the{' '}
                    <a href="/guidelines" className="text-cyber-cyan hover:underline">Community Guidelines</a> for
                    the full enforcement policy.
                  </p>
                </div>
              </div>

              <div className="flex items-start gap-3">
                <Heart className="h-4 w-4 text-cyber-pink flex-shrink-0 mt-0.5" />
                <div>
                  <h3 className="text-white font-semibold mb-1">Badges & Leaderboard</h3>
                  <p className="leading-relaxed">
                    Earn badges for milestones: First Contribution, Prolific Contributor, Schematic Uploader,
                    Salvager, Recipe Master, and more. Check the{' '}
                    <a href="/leaderboard" className="text-cyber-cyan hover:underline">Leaderboard</a> to see top
                    contributors.
                  </p>
                </div>
              </div>
            </div>
          </section>

          {/* Junkbin & Trading */}
          <section id="junkbin" className="card-cyber p-6 scroll-mt-20">
            <div className="flex items-center gap-2 mb-4">
              <Package className="h-5 w-5 text-cyber-yellow" />
              <h2 className="font-display text-lg font-bold text-cyber-yellow tracking-wider">
                JUNKBIN & TRADING
              </h2>
            </div>

            <div className="space-y-4 text-sm text-gray-300">
              <div>
                <h3 className="text-white font-semibold mb-1">Your Junkbin</h3>
                <p className="leading-relaxed">
                  Your junkbin is a personal inventory of electronics parts you <strong className="text-white">have</strong> and
                  parts you <strong className="text-white">want</strong>. Add products or components to your junkbin from
                  their detail pages using the "Add to Junkbin" button. Manage your collection
                  at <a href="/my-junkbin" className="text-cyber-cyan hover:underline">My Junkbin</a>.
                </p>
              </div>

              <div>
                <h3 className="text-white font-semibold mb-1">Have & Want Lists</h3>
                <p className="leading-relaxed">
                  Mark items as <strong className="text-cyber-green">available</strong> or{' '}
                  <strong className="text-gray-400">not for trade</strong>. Set condition (new, working, broken, unknown),
                  quantity, and notes. Toggle visibility between public and private — only public items appear on
                  your profile and in search results.
                </p>
              </div>

              <div>
                <h3 className="text-white font-semibold mb-1">Contacting Owners</h3>
                <p className="leading-relaxed">
                  When you find a part you need in another user's junkbin, click{' '}
                  <strong className="text-white">Contact Owner</strong> to start a conversation. The message is
                  pre-filled with item context. All transactions are person-to-person — Junkbin.io connects people
                  but doesn't handle payments or disputes.
                </p>
              </div>

              <div>
                <h3 className="text-white font-semibold mb-1">Want Notifications</h3>
                <p className="leading-relaxed">
                  When someone adds a part to their public junkbin that matches your want list, you'll receive an
                  email notification (if enabled in your notification preferences).
                </p>
              </div>

              <div>
                <h3 className="text-white font-semibold mb-1">"What Can I Build?"</h3>
                <p className="leading-relaxed">
                  Visit <a href="/buildable" className="text-cyber-cyan hover:underline">What Can I Build?</a> to
                  see community recipes sorted by how many of the required parts you already have. Missing parts
                  link to other users' junkbins where they're available, and you can add them to your want list
                  in one click.
                </p>
              </div>
            </div>
          </section>

          {/* Messaging */}
          <section id="messaging" className="card-cyber p-6 scroll-mt-20">
            <div className="flex items-center gap-2 mb-4">
              <Send className="h-5 w-5 text-cyber-yellow" />
              <h2 className="font-display text-lg font-bold text-cyber-yellow tracking-wider">
                MESSAGING
              </h2>
            </div>

            <div className="space-y-4 text-sm text-gray-300">
              <div>
                <h3 className="text-white font-semibold mb-1">Conversations</h3>
                <p className="leading-relaxed">
                  Your <a href="/messages" className="text-cyber-cyan hover:underline">Inbox</a> shows all
                  conversations, sorted by most recent. Unread conversations are highlighted with a badge count
                  in the header. Messages poll automatically — every 5 seconds when viewing a thread, every 30
                  seconds in the inbox.
                </p>
              </div>

              <div>
                <h3 className="text-white font-semibold mb-1">Starting a Conversation</h3>
                <p className="leading-relaxed">
                  Click any username to visit their profile, then use the message button. You can also
                  start a new conversation from the inbox. The recipient field supports autocomplete search.
                </p>
              </div>

              <div className="flex items-start gap-3">
                <Bell className="h-4 w-4 text-cyber-cyan flex-shrink-0 mt-0.5" />
                <div>
                  <h3 className="text-white font-semibold mb-1">Notifications</h3>
                  <p className="leading-relaxed">
                    Email notifications for new messages can be toggled in your profile under notification
                    preferences. You can also configure notifications for submission reviews, reports, and
                    junkbin matches.
                  </p>
                </div>
              </div>

              <div>
                <h3 className="text-white font-semibold mb-1">Blocking</h3>
                <p className="leading-relaxed">
                  If someone is harassing you, use the block feature to prevent them from messaging you.
                  Blocked users can't start new conversations with you or reply to existing ones. You can
                  also report messages that violate the community guidelines.
                </p>
              </div>
            </div>
          </section>

          <p className="text-center text-xs text-gray-600 font-mono pt-4">
            Last updated: March 2026
          </p>
        </div>
      </div>
    </div>
  );
}
