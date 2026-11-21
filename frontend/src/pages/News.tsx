import { Newspaper, Zap, Cpu, Globe, Wrench, Package, Rocket, ShieldCheck, Sparkles } from 'lucide-react';

interface WeekEntry {
  id: string;
  label: string;
  dates: string;
  color: string;
  icon: React.ReactNode;
  intro: string;
  items: React.ReactNode[];
}

const weeks: WeekEntry[] = [
  {
    id: 'week-19',
    label: 'Update 19',
    dates: 'Nov 20–21, 2026',
    color: 'cyber-purple',
    icon: <Sparkles className="h-5 w-5" />,
    intro:
      "Parts without a photo now get a picture drawn from their own value, and every one of those pictures goes through moderation like any upload. Through-hole resistors are rendered with their colour bands (an unknown tolerance gets a hatched placeholder band, metal-film parts a blue body), ceramic discs carry their three-digit code, electrolytic cans are scaled from catalogue case tables with the value printed lengthwise and the negative stripe marked, surface-mount cans sit on their seat plate, film capacitors wear the Orange Drop print, and power resistors get the white cement block with its rating and value. The same week turned up two classes of wrong values in imported parts — sub-ohm emitter resistors read as megohms, and schematic clock nets read as resistor values — both traced back to their schematics and corrected.",
    items: [
      'Default photos per component type and package, and per-part renderings, each in its own review batch with the source named — a person\'s photo is never displaced by a rendering',
      'Rendered so far: 852 banded resistors, 435 cement power resistors, 299 ceramic discs, over 1,000 electrolytic cans (generic and brand), 30 surface-mount cans, 138 film capacitors',
      'A corrected rendering can replace an earlier one without losing the approval a moderator already gave it',
      'Milliohm emitter resistors that an import had read as megohms ("470m" → 470 MΩ) restored from their own schematic notes; the four circuits checked put the resistor in a TO-3 emitter, where only a sub-ohm part works',
      'Resistors whose "value" was really a clock net, a chip name or a neighbour\'s spec (33R on a 48 MHz line, "RN50" the graphics chip) settled by reading each schematic page; 223 placements moved, chip blocks dropped',
      'Service-manual parts lists: positions printed as a range (C234-245) are every position, in both tables of a two-column page — before, the second table\'s row ran into the first one\'s description',
      'Teardown write-ups as a source: products and parts lists built from the facts in an article, with the article cited and nothing copied',
      'Machines listed with and without their screen size ("Inspiron 3542" / "Inspiron 15 3542") merged into one page under the sized name',
      'Dependabot bumps: pywebpush, django-permissions-policy, django-debug-toolbar and frontend transitive packages',
    ],
  },
  {
    id: 'week-18',
    label: 'Update 18',
    dates: 'Nov 12–18, 2026',
    color: 'cyber-blue',
    icon: <Cpu className="h-5 w-5" />,
    intro:
      "Notebook mainboards arrived as products in their own right, filed by board code and linked to the machines they are fitted in. A board page now says which laptops it went into, a laptop page lists its boards, and a daughterboard knows its mainboard. Thousands of machines the library only knew by name got placeholder pages so those links have somewhere to land, with their names cleaned up to the brand's own spelling. Parts lists are now read straight off the schematics products already carry, chip labels are confirmed against distributors, and valves got substitution tables and specialist dealers. Content made on the development site now flows to the live one every night, unapproved, for moderation there.",
    items: [
      'Boards fitted in devices: part-of and also-in links on both product pages, from exact retail-name matches',
      'Notebook mainboard lane: 3,156 boards from the big ODMs, then 5,328 more (Wistron, Apple, Inventec, Samsung), each with its schematic',
      'Stub machines and stub boards: one spelling per machine, typo\'d family words corrected ("ThinaPad" → "ThinkPad"), twins merged',
      'Facts gathered per source (web search, firmware label, service manual) into the description, each sentence replaced in place on a re-run',
      'eBay listings now feed the "which machine fits this board" research alongside web search',
      'Parts lists read from the schematics products already have (extract_schematic_boms), 4× faster import, two misread forms dropped',
      'Chips read from schematic labels get confirmed by rule or at a distributor, or are dropped as noise; a company\'s old and new names count as one maker',
      'Valves: substitution table, Substitute rows and a second-sources panel on the part page; valve pages name specialist dealers',
      'Equivalents search filters by DigiKey\'s own parameters; product pages get a revision selector',
      'Nightly content publish from development to production (export → media → load), with idempotent descriptions and retired links',
      'Dependencies pinned and audited in CI (Pillow 13, DRF 3.18, rembg 2.0.87, django-allauth 65.22); CI runner gets tesseract, poppler and libmagic like the backend image',
    ],
  },
  {
    id: 'week-17',
    label: 'Update 17',
    dates: 'Nov 1–8, 2026',
    color: 'cyber-green',
    icon: <Package className="h-5 w-5" />,
    intro:
      "The service-manual library went live: 9,526 products and 28,364 components at the first publish, with the electrical parts lists read out of the manuals themselves — Sony, Samsung, Sharp, LG, Onkyo, Panasonic and Yamaha layouts each taught to the reader with real page excerpts as tests. A collection of guitar amplifier, effects pedal and hi-fi schematics joined it with parts lists read by eye off the drawings, fuse rows included. Moderation got a proper overhaul for the volume: an overlay reviewer, undo, reasons that fix a category instead of rejecting a photo, batched approval emails, and PDFs that render on a phone.",
    items: [
      'Service manuals: electrical parts lists read fast and exactly, with the old OCR pass as fallback; BOM scans open to visitors, cached per file',
      'Parts-list reader: Sharp two-column rows, codes and price marks; LG replacement lists; Murata coded capacitors; RKM capacitances (4N7, 2P2); quantity columns; resistor arrays',
      'Schematic labels: ODM value codes for Quanta, Clevo, Inventec, Wistron, MSI, Compal, Tongfang and Gigabyte; crystals give frequency and load; bracketed codes and revision dates are not values',
      'New product categories instrument_amp and effects_pedal; new component types vacuum_tube and potentiometer',
      'Moderation: review in an overlay with feedback to the submitter, undo an approval, "Wrong category" fixes the category, "Poor BG removal" reason, no more rate-limit stalls when approving',
      'Approval and rejection emails batched into one summary per user every five minutes',
      'Products page: newest first, items with a photo first, category menu from the API; moderation on phones draws PDFs with pdf.js',
      'export_content / load_content copy reviewed import content from one site to another, keeping the rows\' dates',
      'Ops: development site rebuilt each day as a scrubbed copy of production; off-host media mirror twice a day; backups skip media too big to archive; certificates ready for shorter Let\'s Encrypt lifetimes',
    ],
  },
  {
    id: 'week-16',
    label: 'Update 16',
    dates: 'Oct 20–31, 2026',
    color: 'cyber-pink',
    icon: <Wrench className="h-5 w-5" />,
    intro:
      "Schematic BOM extraction learned to read the value labels the laptop ODMs actually print — typed Generic parts with graded confidence and grouped rows — and a review screen shows the page crop around each designator so a moderator can see the label the reader saw. CAD-drawn PDFs are read from their text layer, so only scanned pages count against the OCR limit. Component ratings moved into real fields, maker spellings were unified, and ratings the factory BOMs disagree on are settled from the makers' own data.",
    items: [
      'Schematic BOM extraction reads ODM value labels (Quanta, Clevo, Inventec, Wistron, MSI size codes) once the ODM is known',
      'BOM review screen: page crop around each designator, label words, other readings, include toggles',
      'Schematic OCR reads CAD PDFs from their text layer; only scanned pages count to the limit',
      'Component ratings in real fields; disputed ratings settled from makers\' data; one spelling per component maker',
      'Decoders for service-manual vendor parts, arrays and electrolytics; unconfirmed BOM part numbers marked for review; Chinese BOM text translated on import',
      'Firmware dumps imported from bundles with their own review batch; UEFI capsule and vendor flash image extensions accepted',
      'Product photos found by image search imported for review',
      'Datasheet descriptions cleaned of web menus and copyright notices',
      'Per-user page cache fixed; cached pages cleared when an import batch is approved',
    ],
  },
  {
    id: 'week-15',
    label: 'Update 15',
    dates: 'Oct 14–17, 2026',
    color: 'cyber-cyan',
    icon: <ShieldCheck className="h-5 w-5" />,
    intro:
      "Groundwork for importing a library: board BOM bundles become products, components and cross-references in one command, bundle documents attach as unapproved schematics, and matched datasheets attach to components. Part lookups fall back to DigiKey and Mouser when the primary source refuses, and missing parts can be searched for at distributors and added. On the server side, Prometheus got locked down, page security headers came back, fail2ban started again, and robots.txt and the sitemap are real files instead of the app shell.",
    items: [
      'import_board_bom: board BOM bundles to products, components and cross-refs; documents attached as unapproved schematics; updates products in place; --documents-only',
      'import_datasheets: attach matched datasheet files to components, creating the component when the match asks for it',
      'Part lookups fall back to DigiKey and Mouser; quota and refusal errors reported instead of a generic failure',
      'Search distributors for missing parts, add them, and ask what product needs them',
      'Points, clean display of imported data, and import batch review ahead of the library publish',
      'Revision shown on product titles; product gallery opens on the chosen preview image',
      'Prometheus locked down, security headers restored, metrics scrape fixed; fail2ban jails that kept it from starting dropped',
      'Real robots.txt and sitemap.xml; distro certbot timer masked so cron is the only renewal path',
    ],
  },
  {
    id: 'week-14',
    label: 'Update 14',
    dates: 'Sep 9–24, 2026',
    color: 'cyber-yellow',
    icon: <Globe className="h-5 w-5" />,
    intro:
      "A quiet month on features and a loud one on plumbing. Certificate renewal had been failing silently; it now renews, alerts go through the app's own SMTP relay instead of mail(1), the disk monitor orders itself after the network is up, and the runbook documents every monitoring timer. Admins can also pick which photo represents a product.",
    items: [
      'Fixed silently-failing certificate renewal, systemd unit paths and the backup cron',
      'Cert and disk alerts delivered through the app\'s SMTP relay; recipient read from .env',
      'Monitoring timers documented in the runbook; deprecated nginx http2 listen syntax replaced',
      'Admins choose a product\'s preview image',
    ],
  },
  {
    id: 'week-13',
    label: 'Update 13',
    dates: 'Aug 30–31, 2026',
    color: 'cyber-blue',
    icon: <ShieldCheck className="h-5 w-5" />,
    intro:
      "Version 0.9.7, the hardening release. Django went from 5.1 to 5.2 and then 6.0, Python to 3.12, every backend dependency got pinned and audited in CI, and all 28 open npm advisories were closed. A security pass fixed an admin IP-allowlist bypass through a spoofed header, a stored-XSS risk in SVG schematic uploads, and a service-worker cache that could leak one user's API responses to another. Repair Reports became a structured tab on product pages, and products can cite where their information came from.",
    items: [
      'Django 5.2.17 → 6.0.8, Python 3.11 → 3.12, django-debug-toolbar 7.1; backend dependencies pinned to exact versions and audited by pip-audit in CI; Dependabot configured for pip, npm and GitHub Actions',
      'All 28 frontend npm security vulnerabilities fixed; GitHub Actions bumped',
      'Security: admin IP allowlist no longer bypassable via X-Forwarded-For; SVG schematic uploads sanitised; service worker stops caching /api/ responses; message attachments served through an authenticated endpoint; firmware uploads validated by content; SECURITY.md added',
      'Structured Repair Reports tab on product pages',
      'Clickable source-URL attribution on product pages; RECESSIM wiki product import',
      'N+1 query fixes across the Swap Shop, messaging inbox and products app; indexes on reputation and contribution counts; admin bulk-edit uses bulk_update',
      'Background-removal model pre-warmed on worker startup; deploy no longer stalls two minutes on the migrate step',
      'Login false-failures from a throttle-scope collision fixed; password change on its own rate-limit scope; BOM import cap raised to 10 MB',
    ],
  },
  {
    id: 'week-12',
    label: 'Update 12',
    dates: 'Aug 27, 2026',
    color: 'cyber-purple',
    icon: <Sparkles className="h-5 w-5" />,
    intro:
      "Trusted contributors were seeing a \"pending moderator review\" message on submissions that had actually gone live instantly — fixed at the root, in both the API response and the UI. The homepage got a cleanup: a stale launch banner and a blinking beta-tester callout are gone, replaced by a \"Find a Part\" search that actually shows off what the database is for, and a mascot-branded home-screen icon. Component search now understands real values — searching \"10k\" finds resistors near 10kΩ, not just anything with \"10k\" in its description. And uploaded photos can now have their backgrounds automatically removed, entirely on our own server — no third-party API, no per-image cost — with moderator tools to apply it retroactively to images that predate the feature.",
    items: [
      'Fixed trusted-contributor submissions showing "pending moderator review" even when already published — the server response never carried the actual approval status',
      'Homepage refresh: dropped a stale launch banner and a blinking beta-tester callout, added a "Find a Part" search widget, new mascot-based PWA/app icon',
      'Structured component value search — "10k", "4.7uF", "16MHz" match real specifications within a tolerance band, not substring text search; new Value and Package filters on the Components page',
      'Self-hosted background removal for product/component photos (rembg/ONNX, no external API) — automatic on upload for hero/package shots, with a before/after compare and Advanced controls',
      'Moderator tool to retroactively apply background removal to already-published images, with Undo',
      'Open-hardware seed data: Arduino Uno Rev3 and Framework Laptop 13, sourced from official manufacturer schematics/BOMs under permissive licenses',
    ],
  },
  {
    id: 'week-11',
    label: 'Update 11',
    dates: 'Aug 15, 2026',
    color: 'cyber-blue',
    icon: <Wrench className="h-5 w-5" />,
    intro:
      "A lot of components in the database had blank descriptions and no recognizable value — imported from old BOMs whose only real signal was a scribbled note. A new backfill pass recovered construction type, tolerance, and rating for thousands of entries, and cross-referenced live data from Nexar/Octopart to fill in what raw notes couldn't. Moderators also got a proper bulk-edit tool for cleaning up components at scale.",
    items: [
      'backfill_component_values command recovers resistor/capacitor/inductor values from raw BOM notes text',
      'Component descriptions backfilled with construction type, tolerance, and voltage/wattage rating',
      'Nexar/Octopart enrichment for component descriptions, recognizing "Ref. No." style BOM columns',
      'New PDF part-number reconciler',
      'Product-scoped BOM filter and a generic bulk-edit action added to the Component admin',
      'Service worker registration errors are now caught instead of surfacing as unhandled exceptions',
    ],
  },
  {
    id: 'week-10',
    label: 'Update 10',
    dates: 'Aug 10–13, 2026',
    color: 'cyber-green',
    icon: <Package className="h-5 w-5" />,
    intro:
      "Schematic uploads stopped being PDF-only — KiCad, Altium, Eagle, STEP, DXF, and board-view repair formats (.pcb, .tvw, .fz) are all fair game now, alongside plain zip archives. And Sentry went live in production: real error tracking with release tagging, frontend and backend both, plus cron monitoring so a silently-failing scheduled task doesn't stay silent.",
    items: [
      'Schematic uploads now accept KiCad, Altium, Eagle, STEP, and DXF files',
      'Board-view repair formats added: .pcb, .tvw, .fz, plus plain .zip archives',
      'Full Sentry setup: frontend error tracking, release tagging, and Celery cron monitoring',
      'Backend and nginx logs now persist across container recreation',
      'Removed a hardcoded Weblate API token from the translation sync script',
    ],
  },
  {
    id: 'week-9',
    label: 'Update 9',
    dates: 'Aug 8–9, 2026',
    color: 'cyber-pink',
    icon: <Rocket className="h-5 w-5" />,
    intro:
      "Junkbin.io got featured on Hackaday — and the comment section told us exactly where the rough edges were. The repo went public. A submission-throttling bug that silently ate photo uploads after the first few got root-caused and fixed. A mobile image-loading bug that looked like a browser crash turned out to be native lazy-loading missing images that were already on-screen when React swapped them in. And two feature requests landed the same day: firmware recovery uploads and OCR-based BOM extraction from scanned service manuals.",
    items: [
      <>
        Featured on Hackaday:{' '}
        <a
          href="https://hackaday.com/2026/08/08/junkbin-a-way-to-efficiently-reuse-your-old-electronics/"
          target="_blank"
          rel="noopener noreferrer"
          className="text-cyber-cyan hover:underline"
        >
          "Junkbin: A Way To Efficiently Reuse Your Old Electronics"
        </a>
      </>,
      'junkbin.io repository made public',
      'Fixed a submission-throttling bug where a few photos on one product submission could burn through the same rate-limit bucket as spam prevention, silently dropping later uploads',
      'Fixed images that were already in the viewport failing to load — native lazy-loading\'s eligibility check ran before the element existed in the DOM; replaced with a self-contained IntersectionObserver',
      'Firmware upload support with an EEPROM component type and per-product firmware counters',
      'OCR-based schematic BOM extraction from scanned service manuals, restricted to actual service-manual/BOM documents',
      'Users can now change their own username or delete their own account',
      'Email notifications when a submission is approved or rejected',
      'Fixed a stale moderation queue that didn\'t update immediately after approving/rejecting',
      '.jfif image uploads allowed (was missing from every extension allow-list)',
      'Version bumped to 0.9.6',
    ],
  },
  {
    id: 'week-8',
    label: 'Update 8',
    dates: 'Jun 11 – Jul 21, 2026',
    color: 'cyber-yellow',
    icon: <ShieldCheck className="h-5 w-5" />,
    intro:
      "Version 0.9.5. Submitting a product or component that already exists now surfaces a clickable card linking straight to the existing entry instead of a bare validation error. Global search started reaching into teardown notes, schematic notes, and comments, not just titles. AVIF images can be uploaded directly. And SSL certificates now renew themselves — one less thing to remember.",
    items: [
      <>
        Exhibited at OpenSauce (Jul 17–19) —{' '}
        <a
          href="https://www.opensauce.com/exhibits/junkbin-io"
          target="_blank"
          rel="noopener noreferrer"
          className="text-cyber-cyan hover:underline"
        >
          see the showcase page
        </a>
      </>,
      'Duplicate-submission detection: submitting a product/component that already exists shows a linkable suggestion card (thumbnail, category, description excerpt) instead of a generic error',
      'Global search now searches teardown notes, schematic notes, and comments, not just titles and descriptions',
      'AVIF image upload support',
      'Fixed zoomed-in thumbnails on square product photos; thumbnail cache strategy switched to just-in-time regeneration',
      'New "Appliance" product category',
      'Seed data for 11 community-restored IoT devices orphaned by manufacturer shutdown (Wink Hub, Iris Smart Hub, Insteon Hub, MyQ, Piper NV, Canary, WeMo Switch, Sonoff Basic R2, Shelly 1)',
      "Let's Encrypt certificate auto-renewal added to the deploy script",
      'Fixed newsletter subscribe throttle sharing a cache key with the global anonymous throttle',
    ],
  },
  {
    id: 'week-7',
    label: 'Update 7',
    dates: 'Mar 7 – Apr 2, 2026',
    color: 'cyber-cyan',
    icon: <Globe className="h-5 w-5" />,
    intro:
      "Version 0.9.5 groundwork. A self-hosted CI/CD pipeline started running the test suite on every push. Then the last mile of internationalization: all 17 non-English languages pushed to 100% coverage via DeepL and MyMemory. A proper About and Contact page arrived, with a Konami-code Easter egg for anyone still reading the source. And a pass of infrastructure hardening closed out the stretch — direct-IP access blocked, duplicate alert emails fixed, and monitoring got less trigger-happy about backup-time CPU spikes.",
    items: [
      'Self-hosted CI/CD pipeline with a dedicated dev runner — backend and frontend tests run on every push',
      'All 17 non-English languages reached 100% translation coverage via DeepL and MyMemory machine translation',
      'About and Contact pages added, plus a Konami-code Easter egg',
      'Custom favicon, NUSPI branding, and a proper loading screen',
      'Fixed the CI test environment (PostgreSQL for search-vector support, jsdom URL polyfill, cookie-based auth test rewrite)',
      'Direct-IP/unknown-host HTTPS access blocked; Weblate ALLOWED_HOSTS hardened',
      'Fixed duplicate email notifications caused by three separate bugs',
      'Reduced false-positive CPU alerts triggered by nightly backup compression',
      'Fixed nginx health check failing on an unmatched server_name',
    ],
  },
  {
    id: 'week-6',
    label: 'Update 6',
    dates: 'Mar 5–6, 2026',
    color: 'cyber-green',
    icon: <Globe className="h-5 w-5" />,
    intro:
      "Version 0.9.4. The translation completion release. Every last page and form — all 14 remaining pages and 2 form components — got wired to the i18n system, bringing the total to 1,044 translation keys across 37 namespace sections. Then Weblate went live at translate.junkbin.io, giving community translators a proper home with automated sync back to the main repo. Meanwhile, the JavaScript bundle got a full code-splitting treatment: the 862 KB monolith became a 232 KB app shell with lazy-loaded per-page chunks and cacheable vendor libraries. Faster first loads, better caching, zero visual change.",
    items: [
      'i18n Phase 2 complete — 14 pages wired: Recipes, Schematics, Messages, Profile, ProductDetail, ComponentDetail, Submit, SubmitRecipe, RecipeDetail, UserProfile, MessageThread, NewConversation, MyJunkbin, MySubmissions',
      'SchematicUpload and AddComponentForm components wired — all form dropdowns, labels, and error messages now translated',
      '1,044 translation keys total across 37 namespace sections — new additions include schematics.upload.*, components.add.*, common.condition.*, product_detail condition/status badges',
      'All 17 non-English locale files normalised to 1,044 keys — English fallback populated for Phase 2 additions so no raw key strings are ever shown',
      'Weblate community translation portal launched at translate.junkbin.io — contribute or improve translations in your language, no git required',
      'Automated Weblate→main repo sync — translations committed to the locales repo automatically open a pull request on the main repo via GitHub Actions',
      'MyMemory machine translation bootstrapped — 8 languages auto-translated (200+ strings each) as a starting point for community review',
      'JS bundle split — vite.config.ts manualChunks + React.lazy() in App.tsx; vendor libraries (React, Router, TanStack Query, i18next, Lucide, Axios) now in separate cacheable chunks',
      'Version bumped to 0.9.4',
    ],
  },
  {
    id: 'week-5',
    label: 'Update 5',
    dates: 'Mar 3–4, 2026',
    color: 'cyber-cyan',
    icon: <Globe className="h-5 w-5" />,
    intro:
      "Version 0.9.3. The polish release. Every corner of the site that was still speaking hardcoded English got translated — the Guidelines page, all five HTML email templates, every validation error message. The Django locale infrastructure is now fully in place: 353 extractable strings, .po files for all 18 languages, ready for community translators to fill. Three new languages joined the family: Romanian, Hungarian, and Turkish. PCBTracer got deeper wired in — open any product's PCB image directly in the tracer, and after a BOM import the Swap Shop is one click away. GitHub OAuth went live. And API documentation is now admin-only.",
    items: [
      'GitHub OAuth: sign in or register with your GitHub account — popup-based Authorization Code flow, server-side token exchange, auto account linking',
      '18 languages: Romanian, Hungarian, and Turkish added to the UI switcher',
      'Guidelines page fully translated: all ~45 body strings now use i18n keys',
      'HTML email templates translated: email verification, password reset, newsletter confirm, account action, and new message emails all use {% trans %} tags',
      'Serializer validation errors wrapped in gettext_lazy — translatable across all 18 backend locales',
      'Django .po/.mo locale infrastructure: 353 translatable strings extracted, compilemessages run for all 18 languages',
      'Translation contributor guide added: docs/CONTRIBUTING_TRANSLATIONS.md covers both JSON and .po workflows',
      '"Open in PCBTracer" button on product pages — opens the current PCB image directly in PCBTracer',
      'PCBTracer hint on the Submit page — shown when submitting a product, links to pcbtracer.com',
      'BOM import → Swap Shop shortcut: after a successful import the "Check Swap Shop" link appears filtered to components',
      'API schema and docs endpoints restricted to admin users',
    ],
  },
  {
    id: 'week-4',
    label: 'Update 4',
    dates: 'Feb 28 – Mar 2, 2026',
    color: 'cyber-yellow',
    icon: <Package className="h-5 w-5" />,
    intro:
      "Version 0.9.0. The milestone release. The Swap Shop arrived, letting the community browse each other's parts lists for the first time. Datasheets got their own upload and review pipeline. Direct messages gained file attachments with an image lightbox. And then — fifteen languages. From English to Ukrainian, Junkbin.io now speaks to the global repair community in their own words. This is what beta looks like when you mean it.",
    items: [
      'Full internationalization: 15 languages — English, French, Spanish, Portuguese, German, Italian, Dutch, Polish, Czech, Slovak, Croatian, Serbian, Slovenian, Russian, and Ukrainian',
      'Language auto-detected from the browser on first visit; manual switcher via the globe icon in the header',
      'Preferred language saved to your profile so it follows you across devices when logged in',
      'Swap Shop launched: community-wide browse page with HAVE/WANT tabs and search',
      'File attachments in direct messages — send images and documents in conversations',
      'Image lightbox for message attachments — click to view full-size',
      'Component datasheet file upload: PDF and document support with a moderator review queue',
      'Component images added to the pending moderation queue',
      'Site versioning: v0.9.0 tagged with build timestamp visible in the footer',
      'X (Twitter) profile and banner logo assets published',
      'Moderation notice shown after submission instead of navigating the user away',
    ],
  },
  {
    id: 'week-3',
    label: 'Update 3',
    dates: 'Feb 17–20, 2026',
    color: 'cyber-green',
    icon: <Wrench className="h-5 w-5" />,
    intro:
      "Great features deserve great documentation, great photos, and a great mobile experience. Update 3 was all about making Junkbin.io feel like a real product: in-app guides, a fully editable profile, mobile camera capture so you can photograph components right from your workbench, and the safety features users had been asking for — block, unblock, and report in the chat window.",
    items: [
      'In-app documentation hub: user guide covering every feature, browsing, contributing, and the junkbin',
      'Component images displayed on listing pages with smart type/package default images',
      'Mobile camera capture — photograph PCB components directly from your phone and upload in one tap',
      'Component image uploads with server-side thumbnail generation',
      'Profile editing: display name, bio, and avatar all editable from the profile page',
      'Password change from within the profile — no need to go through the reset flow',
      'Product deletion, schematic tracking, and My Reports all added to the profile dashboard',
      'Block, unblock, and report buttons integrated into the chat window header',
      'Submit and messaging icons added to the mobile header for quicker access',
    ],
  },
  {
    id: 'week-2',
    label: 'Update 2',
    dates: 'Feb 13–16, 2026',
    color: 'cyber-pink',
    icon: <Cpu className="h-5 w-5" />,
    intro:
      "If Update 1 was the ignition, Update 2 was the turbocharger. In four days, Junkbin.io grew from a component lookup tool into a full community platform: direct messaging, a trading system, a recipe engine, achievement badges, Google OAuth, analytics dashboards, and live component pricing. This was the feature flood that defined what Junkbin.io would become.",
    items: [
      'User-to-user direct messaging with adaptive polling',
      'Community guidelines enforcement: content filtering, warnings, and strike notifications',
      'User discovery and public profiles — find fellow repairers and start conversations',
      'Granular email notification preferences per user',
      'Personal Junkbin: track components you have, create want lists, get trade match notifications',
      '"What Can I Build?" recipes page with a BOM matching engine against your junkbin',
      'Badge and achievement system — earn recognition for contributions',
      'Component verification voting: confirm or dispute entries to improve data quality',
      'Google OAuth login — sign in with your Google account',
      'Advanced analytics: search trends, engagement metrics, and a live dashboard',
      'Nexar/Octopart integration for live component pricing and distributor availability',
      'Image uploads for products — any registered user can contribute photos',
      'Image moderation workflow: photos are reviewed before going live',
      'My Submissions page — track everything you\'ve contributed and its review status',
    ],
  },
  {
    id: 'week-1',
    label: 'Update 1',
    dates: 'Jan 30 – Feb 2, 2026',
    color: 'cyber-cyan',
    icon: <Zap className="h-5 w-5" />,
    intro:
      "It began not with a whimper, but with a commit. In just four days, Junkbin.io went from a blank repository to a fully deployed, production-ready platform. The right-to-repair community now has its own searchable component database — and it's live.",
    items: [
      'Launched the Junkbin.io MVP: full product and component database with cross-referencing',
      'One-command deployment for Ubuntu, Fedora, Arch, and Debian',
      'Let\'s Encrypt SSL provisioned automatically — HTTPS from the very first deploy',
      'Email verification on registration',
      'Login protection with clear, helpful messaging on too many failed attempts',
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
  'cyber-purple': {
    border: 'border-cyber-purple/40',
    bg: 'bg-cyber-purple/10',
    text: 'text-cyber-purple',
    dot: 'bg-cyber-purple',
    badge: 'border-cyber-purple/50 text-cyber-purple bg-cyber-purple/10',
  },
  'cyber-blue': {
    border: 'border-cyber-blue/40',
    bg: 'bg-cyber-blue/10',
    text: 'text-cyber-blue',
    dot: 'bg-cyber-blue',
    badge: 'border-cyber-blue/50 text-cyber-blue bg-cyber-blue/10',
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
          <p className="text-xs text-gray-500 font-mono">Development timeline — grouped by update</p>
        </div>
      </div>

      <p className="text-gray-400 text-sm mb-10 max-w-2xl">
        A living record of everything that's been built, fixed, and shipped — straight from the commit log.
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
