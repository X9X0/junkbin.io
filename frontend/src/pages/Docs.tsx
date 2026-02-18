import { useState, useEffect } from 'react';
import {
  BookOpen, Users, Search, Upload, MessageSquare, Package, Code,
  Server, Terminal, ChevronRight, Menu, X, ExternalLink, Keyboard,
  Shield, Star, Heart, Send, Bell, Cpu, Wrench,
} from 'lucide-react';

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
  { id: 'community', label: 'Community', icon: <Users className="h-4 w-4" />, color: 'text-cyber-green' },
  { id: 'junkbin', label: 'Junkbin & Trading', icon: <Package className="h-4 w-4" />, color: 'text-cyber-yellow' },
  { id: 'messaging', label: 'Messaging', icon: <MessageSquare className="h-4 w-4" />, color: 'text-cyber-yellow' },
];

const devSections: Section[] = [
  { id: 'api', label: 'API Overview', icon: <Code className="h-4 w-4" />, color: 'text-cyber-pink' },
  { id: 'self-hosting', label: 'Self-Hosting', icon: <Server className="h-4 w-4" />, color: 'text-cyber-pink' },
  { id: 'commands', label: 'Management Commands', icon: <Terminal className="h-4 w-4" />, color: 'text-cyber-cyan' },
  { id: 'contributing-code', label: 'Contributing Code', icon: <Wrench className="h-4 w-4" />, color: 'text-cyber-cyan' },
];

export default function Docs() {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [activeSection, setActiveSection] = useState('getting-started');

  useEffect(() => {
    const handleScroll = () => {
      const sections = [...userSections, ...devSections];
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
    <div className="mx-auto max-w-7xl px-4 py-8">
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
        Everything you need to use, contribute to, and self-host Junkbin.io
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
            <div>
              <h3 className="font-mono text-xs font-semibold text-gray-500 tracking-wider mb-2">
                DEVELOPER GUIDE
              </h3>
              <ul className="space-y-1">
                {devSections.map((s) => (
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
                  Alternatively, sign in instantly with <strong className="text-white">Google</strong> using the
                  "Continue with Google" button on the login page.
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

          {/* ─── DEVELOPER GUIDE ─── */}

          <div className="border-t border-cyber-light/30 pt-8">
            <p className="font-mono text-xs text-gray-500 tracking-wider mb-4">DEVELOPER GUIDE</p>
          </div>

          {/* API Overview */}
          <section id="api" className="card-cyber p-6 scroll-mt-20">
            <div className="flex items-center gap-2 mb-4">
              <Code className="h-5 w-5 text-cyber-pink" />
              <h2 className="font-display text-lg font-bold text-cyber-pink tracking-wider">
                API OVERVIEW
              </h2>
            </div>

            <div className="space-y-4 text-sm text-gray-300">
              <p className="leading-relaxed">
                Junkbin.io exposes a full REST API built with Django REST Framework. Interactive documentation
                is available at{' '}
                <a href="/api/docs/" target="_blank" rel="noopener noreferrer" className="text-cyber-cyan hover:underline inline-flex items-center gap-1">
                  /api/docs/ <ExternalLink className="h-3 w-3" />
                </a>{' '}
                (Swagger/OpenAPI via drf-spectacular).
              </p>

              <div>
                <h3 className="text-white font-semibold mb-1">Authentication</h3>
                <p className="leading-relaxed">
                  The API uses JWT (JSON Web Tokens) with short-lived access tokens and refresh token rotation.
                  Obtain tokens via <code className="text-cyber-pink bg-cyber-dark px-1">POST /api/auth/login/</code>.
                  Include the access token in requests as{' '}
                  <code className="text-cyber-pink bg-cyber-dark px-1">Authorization: Bearer &lt;token&gt;</code>.
                </p>
              </div>

              <div>
                <h3 className="text-white font-semibold mb-1">Rate Limits</h3>
                <p className="leading-relaxed">
                  API endpoints are rate-limited to prevent abuse. Default limits are configurable via environment
                  variables. Auth endpoints have stricter limits. Rate limit headers are included in every response.
                </p>
              </div>

              <div>
                <h3 className="text-white font-semibold mb-2">Key Endpoints</h3>
                <div className="font-mono text-xs space-y-1">
                  {[
                    ['GET', '/api/products/', 'List / search products'],
                    ['GET', '/api/components/', 'List / search components'],
                    ['GET', '/api/components/{id}/products/', 'Cross-reference'],
                    ['GET', '/api/schematics/', 'List schematics'],
                    ['GET', '/api/search/', 'Global search'],
                    ['POST', '/api/submissions/', 'Submit content'],
                    ['GET', '/api/junkbin/', 'Public junkbin items'],
                    ['GET', '/api/recipes/', 'Community recipes'],
                  ].map(([method, path, desc]) => (
                    <div key={path} className="flex gap-3">
                      <span className={method === 'GET' ? 'text-cyber-green' : 'text-cyber-yellow'}>
                        {method}
                      </span>
                      <span className="text-gray-400">{path}</span>
                      <span className="text-gray-600">— {desc}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </section>

          {/* Self-Hosting */}
          <section id="self-hosting" className="card-cyber p-6 scroll-mt-20">
            <div className="flex items-center gap-2 mb-4">
              <Server className="h-5 w-5 text-cyber-pink" />
              <h2 className="font-display text-lg font-bold text-cyber-pink tracking-wider">
                SELF-HOSTING
              </h2>
            </div>

            <div className="space-y-4 text-sm text-gray-300">
              <div>
                <h3 className="text-white font-semibold mb-1">Prerequisites</h3>
                <ul className="list-disc list-inside space-y-1 text-gray-400">
                  <li>Linux server (Ubuntu 22.04+, Debian 12+, Fedora 39+, Arch, CentOS/RHEL 9+)</li>
                  <li>2 GB RAM minimum, 4 GB recommended</li>
                  <li>10 GB disk space</li>
                  <li>Domain name (for SSL)</li>
                  <li>Ports 80 and 443 available</li>
                </ul>
              </div>

              <div>
                <h3 className="text-white font-semibold mb-1">Quick Deploy</h3>
                <p className="leading-relaxed mb-2">
                  The automated deploy script handles everything — dependencies, Docker, SSL, firewall, and fail2ban:
                </p>
                <pre className="bg-cyber-dark border border-cyber-light/30 p-3 overflow-x-auto text-xs font-mono">
                  <code>{`git clone https://github.com/junkbin/junkbin.io.git
cd junkbin.io
sudo bash deployment/junkbin-deploy.sh`}</code>
                </pre>
                <p className="text-gray-500 mt-2">
                  The script auto-detects your Linux distribution and walks you through configuration interactively.
                </p>
              </div>

              <div>
                <h3 className="text-white font-semibold mb-1">Docker Compose (Manual)</h3>
                <p className="leading-relaxed mb-2">
                  For manual setup, copy <code className="text-cyber-pink bg-cyber-dark px-1">.env.example</code> to{' '}
                  <code className="text-cyber-pink bg-cyber-dark px-1">.env</code>, configure your settings, then:
                </p>
                <pre className="bg-cyber-dark border border-cyber-light/30 p-3 overflow-x-auto text-xs font-mono">
                  <code>{`cp .env.example .env
# Edit .env with your settings
docker compose up -d
docker compose exec backend python manage.py migrate
docker compose exec backend python manage.py createsuperuser
docker compose exec backend python manage.py collectstatic --noinput`}</code>
                </pre>
              </div>

              <div>
                <h3 className="text-white font-semibold mb-1">Essential Environment Variables</h3>
                <div className="font-mono text-xs space-y-1">
                  {[
                    ['SECRET_KEY', 'Django secret key (generate a unique one)'],
                    ['POSTGRES_PASSWORD', 'PostgreSQL password'],
                    ['ALLOWED_HOSTS', 'Your domain name(s)'],
                    ['SITE_URL', 'Full URL (https://yourdomain.com)'],
                    ['EMAIL_HOST / EMAIL_HOST_PASSWORD', 'SMTP for email delivery'],
                    ['REDIS_PASSWORD', 'Redis password'],
                  ].map(([key, desc]) => (
                    <div key={key} className="flex gap-3">
                      <span className="text-cyber-green whitespace-nowrap">{key}</span>
                      <span className="text-gray-500">— {desc}</span>
                    </div>
                  ))}
                </div>
                <p className="text-gray-500 mt-2">
                  See <code className="text-cyber-pink bg-cyber-dark px-1">.env.example</code> for the full reference with
                  all ~50 configurable variables.
                </p>
              </div>

              <div>
                <h3 className="text-white font-semibold mb-1">Maintenance Scripts</h3>
                <div className="font-mono text-xs space-y-1 text-gray-400">
                  <div><span className="text-cyber-cyan">deployment/update.sh</span> — Pull, rebuild, migrate, restart</div>
                  <div><span className="text-cyber-cyan">deployment/backup.sh</span> — Backup database + media</div>
                  <div><span className="text-cyber-cyan">deployment/restore.sh</span> — Interactive restore menu</div>
                </div>
              </div>
            </div>
          </section>

          {/* Management Commands */}
          <section id="commands" className="card-cyber p-6 scroll-mt-20">
            <div className="flex items-center gap-2 mb-4">
              <Terminal className="h-5 w-5 text-cyber-cyan" />
              <h2 className="font-display text-lg font-bold text-cyber-cyan tracking-wider">
                MANAGEMENT COMMANDS
              </h2>
            </div>

            <div className="text-sm text-gray-300">
              <p className="leading-relaxed mb-4">
                Run via <code className="text-cyber-pink bg-cyber-dark px-1">docker compose exec backend python manage.py &lt;command&gt;</code>
              </p>

              <div className="overflow-x-auto">
                <table className="w-full text-xs font-mono">
                  <thead>
                    <tr className="text-left text-gray-500 border-b border-cyber-light/30">
                      <th className="pb-2 pr-4">Command</th>
                      <th className="pb-2 pr-4">App</th>
                      <th className="pb-2">Description</th>
                    </tr>
                  </thead>
                  <tbody className="text-gray-400">
                    {[
                      ['seed_data [--flush]', 'products', '10 products, ~93 components, ~101 cross-references'],
                      ['import_flipper_schematics [--flush]', 'products', 'Import 15 Flipper Zero schematic PDFs'],
                      ['import_flipper_bom', 'products', 'Import Flipper Zero BOM from Excel'],
                      ['backfill_badges', 'users', 'Backfill badges for existing users'],
                      ['rebuild_search_vectors', 'api', 'Rebuild PostgreSQL full-text search indexes'],
                      ['setup_notifications', 'api', 'Configure admin notification schedule'],
                      ['send_launch_email', 'newsletter', 'Send launch announcement email'],
                    ].map(([cmd, app, desc]) => (
                      <tr key={cmd} className="border-b border-cyber-light/10">
                        <td className="py-2 pr-4 text-cyber-green whitespace-nowrap">{cmd}</td>
                        <td className="py-2 pr-4 text-gray-500">{app}</td>
                        <td className="py-2 text-gray-400">{desc}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </section>

          {/* Contributing Code */}
          <section id="contributing-code" className="card-cyber p-6 scroll-mt-20">
            <div className="flex items-center gap-2 mb-4">
              <Wrench className="h-5 w-5 text-cyber-cyan" />
              <h2 className="font-display text-lg font-bold text-cyber-cyan tracking-wider">
                CONTRIBUTING CODE
              </h2>
            </div>

            <div className="space-y-4 text-sm text-gray-300">
              <div>
                <h3 className="text-white font-semibold mb-1">Repository Structure</h3>
                <p className="leading-relaxed">
                  The monorepo contains <code className="text-cyber-pink bg-cyber-dark px-1">backend/</code> (Django),{' '}
                  <code className="text-cyber-pink bg-cyber-dark px-1">frontend/</code> (React/Vite),{' '}
                  <code className="text-cyber-pink bg-cyber-dark px-1">deployment/</code> (scripts, nginx, monitoring), and{' '}
                  <code className="text-cyber-pink bg-cyber-dark px-1">docs/</code>. See{' '}
                  <code className="text-cyber-pink bg-cyber-dark px-1">docs/PROJECT_STRUCTURE.md</code> for the
                  complete directory tree with annotations.
                </p>
              </div>

              <div>
                <h3 className="text-white font-semibold mb-1">Tech Stack</h3>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 mt-2">
                  <div className="flex items-center gap-2">
                    <Cpu className="h-3 w-3 text-cyber-pink" />
                    <span className="text-gray-400">Django 5.x + DRF + PostgreSQL 15</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <Cpu className="h-3 w-3 text-cyber-cyan" />
                    <span className="text-gray-400">React 19 + Vite 7.3 + TypeScript</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <Cpu className="h-3 w-3 text-cyber-green" />
                    <span className="text-gray-400">Redis 7 + Celery task queue</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <Keyboard className="h-3 w-3 text-cyber-yellow" />
                    <span className="text-gray-400">Tailwind CSS + custom cyberpunk theme</span>
                  </div>
                </div>
              </div>

              <div>
                <h3 className="text-white font-semibold mb-1">Running Tests</h3>
                <pre className="bg-cyber-dark border border-cyber-light/30 p-3 overflow-x-auto text-xs font-mono">
                  <code>{`# Backend
cd backend
DJANGO_SETTINGS_MODULE=config.settings.test pytest -v

# Frontend
cd frontend
npm run test`}</code>
                </pre>
              </div>

              <div>
                <h3 className="text-white font-semibold mb-1">Workflow</h3>
                <ol className="list-decimal list-inside space-y-1 text-gray-400">
                  <li>Fork the repository</li>
                  <li>Create a feature branch</li>
                  <li>Write tests for new functionality</li>
                  <li>Ensure all existing tests pass</li>
                  <li>Submit a pull request with a clear description</li>
                </ol>
              </div>
            </div>
          </section>

          <p className="text-center text-xs text-gray-600 font-mono pt-4">
            Last updated: February 2026
          </p>
        </div>
      </div>
    </div>
  );
}
