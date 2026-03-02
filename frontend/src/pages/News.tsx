import { Newspaper, Zap, Cpu, Globe, Shield, Wrench, MessageSquare, BarChart2, Package } from 'lucide-react';

interface WeekEntry {
  id: string;
  label: string;
  dates: string;
  color: string;
  icon: React.ReactNode;
  intro: string;
  items: string[];
}

const weeks: WeekEntry[] = [
  {
    id: 'week-1',
    label: 'Week 1',
    dates: 'Jan 30 – Feb 2, 2026',
    color: 'cyber-cyan',
    icon: <Zap className="h-5 w-5" />,
    intro:
      "It began not with a whimper, but with a commit. In just four days, Junkbin.io went from a blank repository to a fully deployed, SSL-secured, production-hardened platform. The right-to-repair community now has its own searchable component database — and it's live.",
    items: [
      'Launched the Junkbin.io MVP: full product and component database with cross-referencing',
      'Automated Docker deployment script with one-command setup for Ubuntu, Fedora, Arch, and Debian',
      'Let\'s Encrypt SSL provisioned automatically — HTTPS from the very first deploy',
      'Nginx reverse proxy configured for the full stack (backend, frontend, media)',
      'Email verification on registration with Django-signed tokens',
      'CSRF protection: token endpoint, trusted origins, and per-request headers wired up',
      'Security audit remediation day one: IDOR fixes, admin route protection, cookie-based auth, CSP headers',
      'django-axes brute-force lockout with a friendly, helpful error response instead of a blank wall',
      'libmagic file validation in the backend container for safer uploads',
      'SMTP email fully configurable via environment variables with SSL support',
    ],
  },
  {
    id: 'week-2',
    label: 'Week 2',
    dates: 'Feb 13–16, 2026',
    color: 'cyber-pink',
    icon: <Cpu className="h-5 w-5" />,
    intro:
      "If Week 1 was the ignition, Week 2 was the turbocharger. In four days, Junkbin.io grew from a component lookup tool into a full community platform: direct messaging, a trading system, a recipe engine, achievement badges, Google OAuth, analytics dashboards, and live component pricing. This was the feature flood that defined what Junkbin.io would become.",
    items: [
      'User-to-user direct messaging with adaptive polling and a moderation layer',
      'Community guidelines enforcement: content filtering, warnings, and strike notifications',
      'User discovery and public profiles — find fellow repairers and start conversations',
      'Granular email notification preferences per user',
      'Personal Junkbin: track components you have, create want lists, get trade match notifications',
      '"What Can I Build?" recipes page with a BOM matching engine against your junkbin',
      'Badge and achievement system — earn recognition for contributions',
      'Component verification voting: confirm or dispute entries to improve data quality',
      'Google OAuth login with the GSI popup flow and backend ID-token verification',
      'Advanced analytics: Prometheus metrics, Grafana dashboards, search and engagement tracking',
      'Nexar/Octopart integration for live component pricing and distributor availability',
      'Image uploads for products — any authenticated user can contribute photos',
      'Image moderation workflow with approve/reject queue for moderators',
      'My Submissions page — track everything you\'ve contributed and its review status',
      'Pending Content tab in the moderation dashboard for bulk approve/reject',
      'Celery and Celery Beat consolidated onto the shared backend image (leaner, faster)',
      'CSV import/export for components and product-component mappings via the admin panel',
      'Bulk admin tools for reviewing user contributions',
      'Color-coded system health summaries in the daily digest email',
      'Deploy script extended to support RHEL-family distros (Fedora, CentOS, Rocky)',
    ],
  },
  {
    id: 'week-3',
    label: 'Week 3',
    dates: 'Feb 17–20, 2026',
    color: 'cyber-green',
    icon: <Wrench className="h-5 w-5" />,
    intro:
      "Great features deserve great documentation, great photos, and a great mobile experience. Week 3 was all about making Junkbin.io feel like a real product: in-app guides, a fully editable profile, mobile camera capture so you can photograph components right from your workbench, and the missing safety features users had been asking for — block, unblock, and report in the chat window.",
    items: [
      'In-app documentation hub: user guide covering every feature, browsing, contributing, and the junkbin',
      'Log rotation and disk space monitoring with systemd service management scripts',
      'Component images displayed on listing pages with smart type/package default images',
      'Mobile camera capture — photograph PCB components directly from your phone and upload in one tap',
      'Component image uploads with server-side thumbnail generation',
      'Google OAuth credentials wired into Docker Compose for the social login flow',
      'Profile editing: display name, bio, and avatar all editable from the profile page',
      'Password change from within the profile — no need to go through the reset flow',
      'Product deletion, schematic tracking, and My Reports all added to the profile dashboard',
      'Block, unblock, and report buttons integrated into the chat window header',
      'Admin alert emails now correctly link to production URLs instead of localhost',
      'Submit and messaging icons added to the mobile header for quicker access',
      'TypeScript type definitions updated throughout to match backend serializer shapes',
    ],
  },
  {
    id: 'week-4',
    label: 'Week 4',
    dates: 'Feb 28 – Mar 2, 2026',
    color: 'cyber-yellow',
    icon: <Package className="h-5 w-5" />,
    intro:
      "Version 0.9.0. The milestone release. The Swap Shop arrived, letting the community browse each other's parts lists for the first time. Datasheets got their own upload and review pipeline. Direct messages gained file attachments with an image lightbox. And then — fifteen languages. From English to Ukrainian, Junkbin.io now speaks to the global repair community in their own words. This is what beta looks like when you mean it.",
    items: [
      'Component datasheet file upload: PDF and document support with a moderator review queue',
      'Pending datasheet review queue added to the moderation dashboard',
      'Component images added to the pending moderation queue',
      'Swap Shop launched: community-wide browse page with HAVE/WANT tabs and search',
      'Site versioning: v0.9.0 tagged with build timestamp visible in the footer',
      'Operations runbook added for site continuity and disaster recovery',
      'Service worker fixed — was incorrectly intercepting /media/ navigation requests',
      'PDF and document downloads fixed in production (nginx media proxy)',
      'nginx client_max_body_size raised to 50 MB for large datasheet uploads',
      'File attachments in direct messages: send images and documents in conversations',
      'Image lightbox for message attachments — click to view full-size',
      'Attachment file size and image detection bugs fixed',
      'X (Twitter) profile and banner logo assets exported for social media presence',
      'AccessAttempt admin enhanced with lock status column, filter by locked accounts, and bulk reset',
      'Moderation notice shown after submission instead of navigating the user away',
      'Admin session fix: staff no longer hit a 404 when their session expires in the admin panel',
      'Logout reliability fix and server timezone set to America/New_York',
      'Full internationalization shipped: 15 languages — English, French, Spanish, Portuguese, German, Italian, Dutch, Polish, Czech, Slovak, Croatian, Serbian, Slovenian, Russian, and Ukrainian',
      'Language auto-detected from the browser on first visit; manual switcher via the globe icon in the header',
      'Preferred language saved to user profile so it follows you across devices when logged in',
    ],
  },
];

const colorMap: Record<string, { border: string; bg: string; text: string; dot: string; badge: string }> = {
  'cyber-cyan': {
    border: 'border-cyber-cyan/40',
    bg: 'bg-cyber-cyan/10',
    text: 'text-cyber-cyan',
    dot: 'bg-cyber-cyan',
    badge: 'border-cyber-cyan/50 text-cyber-cyan bg-cyber-cyan/10',
  },
  'cyber-pink': {
    border: 'border-cyber-pink/40',
    bg: 'bg-cyber-pink/10',
    text: 'text-cyber-pink',
    dot: 'bg-cyber-pink',
    badge: 'border-cyber-pink/50 text-cyber-pink bg-cyber-pink/10',
  },
  'cyber-green': {
    border: 'border-cyber-green/40',
    bg: 'bg-cyber-green/10',
    text: 'text-cyber-green',
    dot: 'bg-cyber-green',
    badge: 'border-cyber-green/50 text-cyber-green bg-cyber-green/10',
  },
  'cyber-yellow': {
    border: 'border-cyber-yellow/40',
    bg: 'bg-cyber-yellow/10',
    text: 'text-cyber-yellow',
    dot: 'bg-cyber-yellow',
    badge: 'border-cyber-yellow/50 text-cyber-yellow bg-cyber-yellow/10',
  },
};

export default function News() {
  return (
    <div className="mx-auto max-w-4xl px-4 py-8">
      {/* Header */}
      <div className="flex items-center gap-3 mb-2">
        <div className="p-2 bg-cyber-pink/20 border border-cyber-pink/50">
          <Newspaper className="h-6 w-6 text-cyber-pink" />
        </div>
        <div>
          <h1 className="font-display text-2xl font-bold tracking-wider text-white">
            WHAT'S <span className="text-cyber-pink">NEW</span>
          </h1>
          <p className="text-xs text-gray-500 font-mono">Development timeline — grouped by week</p>
        </div>
      </div>

      <p className="text-gray-400 text-sm mb-10 max-w-2xl">
        A living record of everything that's been built, fixed, and shipped — straight from the commit log.
        Every week brings something new to the repair community.
      </p>

      {/* Timeline */}
      <div className="relative">
        {/* Vertical line */}
        <div className="absolute left-6 top-0 bottom-0 w-px bg-cyber-light/20 hidden md:block" />

        <div className="space-y-12">
          {weeks.map((week) => {
            const colors = colorMap[week.color];
            return (
              <div key={week.id} id={week.id} className="relative md:pl-16">
                {/* Timeline dot */}
                <div className="hidden md:flex absolute left-0 top-1 items-center justify-center w-12 h-12 border border-cyber-light/30 bg-cyber-darker">
                  <div className={colors.text}>{week.icon}</div>
                </div>

                {/* Week card */}
                <div className={`border ${colors.border} bg-cyber-darker`}>
                  {/* Card header */}
                  <div className={`px-6 py-4 border-b ${colors.border} ${colors.bg}`}>
                    <div className="flex flex-wrap items-center gap-3">
                      <span className={`font-mono text-xs font-bold px-2 py-0.5 border ${colors.badge}`}>
                        {week.label}
                      </span>
                      <span className="font-mono text-xs text-gray-400">{week.dates}</span>
                    </div>
                  </div>

                  {/* Intro */}
                  <div className="px-6 pt-5 pb-4">
                    <p className="text-gray-300 text-sm leading-relaxed italic border-l-2 pl-4 border-cyber-light/30">
                      {week.intro}
                    </p>
                  </div>

                  {/* Items */}
                  <ul className="px-6 pb-6 space-y-2">
                    {week.items.map((item, i) => (
                      <li key={i} className="flex items-start gap-3 text-sm text-gray-400">
                        <span className={`mt-2 h-1.5 w-1.5 rounded-full flex-shrink-0 ${colors.dot}`} />
                        {item}
                      </li>
                    ))}
                  </ul>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Footer note */}
      <div className="mt-12 border border-cyber-light/20 bg-cyber-darker p-6 text-center">
        <div className="flex items-center justify-center gap-2 mb-2">
          <Globe className="h-4 w-4 text-cyber-cyan" />
          <span className="font-mono text-xs text-gray-400 uppercase tracking-wider">More coming soon</span>
        </div>
        <p className="text-xs text-gray-500 max-w-md mx-auto">
          Junkbin.io is actively developed. Feature requests, bug reports, and contributions are welcome —
          open an issue or pull request on GitHub.
        </p>
      </div>
    </div>
  );
}
