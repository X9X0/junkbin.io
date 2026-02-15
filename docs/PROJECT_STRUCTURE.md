# Junkbin.io - Project Structure

```
junkbin.io/
├── README.md                          # Project overview
├── LICENSE                            # MIT License
├── .gitignore                         # Git ignore rules
├── docker-compose.yml                 # Multi-container orchestration
├── docker-compose.override.yml        # Local dev overrides (no SSL)
├── .env.example                       # Environment variables template
│
├── docs/                              # Public documentation (git-tracked)
│   ├── ROADMAP.md                     # Project roadmap & feature breakdown
│   └── PROJECT_STRUCTURE.md           # This file
│
├── backend/                           # Django backend
│   ├── manage.py                      # Django management script
│   ├── conftest.py                    # Pytest configuration
│   ├── requirements.txt               # Python dependencies
│   ├── Dockerfile                     # Backend container image
│   ├── .dockerignore                  # Docker ignore rules
│   │
│   ├── config/                        # Django project configuration
│   │   ├── __init__.py
│   │   ├── admin.py                   # Custom admin site (sidebar grouping)
│   │   ├── celery.py                  # Celery app configuration
│   │   ├── settings/
│   │   │   ├── __init__.py
│   │   │   ├── base.py                # Common settings
│   │   │   ├── development.py         # Dev-specific settings
│   │   │   ├── production.py          # Prod-specific settings
│   │   │   └── test.py                # Test settings
│   │   ├── urls.py                    # URL routing
│   │   ├── wsgi.py                    # WSGI application
│   │   └── asgi.py                    # ASGI application
│   │
│   ├── apps/                          # Django applications
│   │   │
│   │   ├── users/                     # User management
│   │   │   ├── models.py              # Custom User model (UUID PK, reputation, trust levels, messaging_blocked)
│   │   │   ├── views.py               # Authentication views (incl. GoogleAuthView)
│   │   │   ├── serializers.py         # API serializers
│   │   │   ├── urls.py                # User-specific routes
│   │   │   ├── admin.py               # Admin config (trust/moderator/messaging block actions)
│   │   │   ├── admin_views.py         # Bulk contribution review page
│   │   │   ├── authentication.py      # JWT cookie auth backend
│   │   │   ├── permissions.py         # IsOwnerOrReadOnly, IsModerator, IsTrustedUser
│   │   │   ├── badges.py              # Badge registry, check_and_award_badges(), display helpers
│   │   │   ├── signals.py             # User-related signals (default preferences)
│   │   │   ├── management/
│   │   │   │   └── commands/
│   │   │   │       └── backfill_badges.py  # One-time badge backfill for existing users
│   │   │   └── tests/
│   │   │
│   │   ├── products/                  # Product management
│   │   │   ├── models.py              # Product, ProductImage, Schematic, ProductComment
│   │   │   ├── views.py               # Product CRUD views + comments + BOM import
│   │   │   ├── serializers.py         # Product serializers (with content filter)
│   │   │   ├── urls.py                # Product routes
│   │   │   ├── admin.py               # Product admin + CSV export
│   │   │   ├── filters.py             # Search filters
│   │   │   ├── bom_utils.py           # BOM CSV column auto-detection and validation
│   │   │   ├── tests/
│   │   │   └── management/
│   │   │       └── commands/
│   │   │           ├── seed_data.py             # 10 products, ~93 components, ~101 cross-refs
│   │   │           ├── import_flipper_schematics.py  # 15 Flipper Zero PDFs + datasheets
│   │   │           └── import_flipper_bom.py    # Flipper Zero BOM from Excel
│   │   │
│   │   ├── components/                # Component management
│   │   │   ├── models.py              # Component, ComponentViewStats, ProductComponent, ComponentVote
│   │   │   ├── views.py               # Component CRUD + cross-reference + voting + trending + view tracking
│   │   │   ├── serializers.py         # Component serializers (vote fields)
│   │   │   ├── urls.py
│   │   │   ├── admin.py               # Component admin + CSV import/export
│   │   │   ├── filters.py             # Component search filters
│   │   │   ├── nexar.py               # Nexar/Octopart API client
│   │   │   ├── tasks.py               # Celery tasks (Nexar bulk enrichment)
│   │   │   └── tests/
│   │   │
│   │   ├── submissions/               # Content submission/moderation
│   │   │   ├── models.py              # Submission model
│   │   │   ├── views.py               # Submission workflow (with throttling)
│   │   │   ├── serializers.py
│   │   │   ├── urls.py
│   │   │   ├── admin.py
│   │   │   ├── tasks.py               # Celery tasks (approval/rejection emails)
│   │   │   └── tests/
│   │   │
│   │   ├── reports/                   # User reporting & moderation system
│   │   │   ├── models.py              # Report, UserReview models (with notification triggers)
│   │   │   ├── views.py               # Report handling (with throttling)
│   │   │   ├── serializers.py
│   │   │   ├── urls.py
│   │   │   ├── admin.py               # Report/UserReview admin (clear/warn/suspend actions)
│   │   │   ├── signals.py             # Auto-trigger UserReview on 3 strikes
│   │   │   ├── tasks.py               # Celery tasks (strike/account action notifications)
│   │   │   └── tests/
│   │   │
│   │   ├── messaging/                 # User-to-user messaging
│   │   │   ├── models.py              # Conversation, Message, UserBlock
│   │   │   ├── views.py               # Inbox, thread, send, unread count, blocking
│   │   │   ├── serializers.py         # Message serializers (with content filter)
│   │   │   ├── urls.py
│   │   │   ├── admin.py               # Conversation/Message/UserBlock admin
│   │   │   └── tasks.py               # Celery task (new message email notification)
│   │   │
│   │   ├── junkbin/                   # Personal junkbin (collection & trading)
│   │   │   ├── models.py              # JunkbinItem (have/want, polymorphic product/component via ContentType)
│   │   │   ├── views.py               # JunkbinItemViewSet (CRUD + my_items, my_summary, user_summary, check)
│   │   │   ├── serializers.py         # List/Detail/Create/Update serializers
│   │   │   ├── urls.py                # Router registration
│   │   │   ├── admin.py               # Admin registration with filters
│   │   │   ├── apps.py                # AppConfig
│   │   │   └── tasks.py               # Celery task (want-list match notifications)
│   │   │
│   │   ├── newsletter/                # Newsletter / email collection
│   │   │   ├── models.py              # Subscriber model
│   │   │   ├── views.py               # SubscribeView API
│   │   │   ├── serializers.py         # Input validation
│   │   │   ├── urls.py                # Route: subscribe/
│   │   │   ├── admin.py               # Admin with CSV export
│   │   │   ├── tests.py               # 11 unit tests
│   │   │   └── management/
│   │   │       └── commands/
│   │   │           └── send_launch_email.py  # Launch blast command
│   │   │
│   │   ├── recipes/                   # Recipes (What Can I Build?)
│   │   │   ├── models.py              # Recipe, RecipeBomItem
│   │   │   ├── views.py               # RecipeViewSet (CRUD + buildable + match)
│   │   │   ├── serializers.py         # Recipe serializers
│   │   │   ├── urls.py
│   │   │   ├── admin.py
│   │   │   └── filters.py
│   │   │
│   │   ├── webhooks/                  # Discord/Slack webhook notifications
│   │   │   ├── models.py              # WebhookEndpoint, WebhookDelivery
│   │   │   ├── views.py               # Webhook management views
│   │   │   ├── serializers.py
│   │   │   ├── urls.py
│   │   │   ├── admin.py
│   │   │   ├── formatters.py          # Discord embed + Slack Block Kit formatters
│   │   │   └── tasks.py               # Celery delivery with retry/backoff
│   │   │
│   │   └── api/                       # API configuration
│   │       ├── models.py              # Admin notification models, SearchQuery (analytics)
│   │       ├── urls.py                # API root routing + JWT cookie auth
│   │       ├── views.py               # APIRoot, SearchView, AnalyticsView, HealthCheck, Stats
│   │       ├── metrics.py             # Custom Prometheus counters/histograms (searches, views, submissions)
│   │       ├── admin.py               # Admin notification admin
│   │       ├── admin_views.py         # System status dashboard view
│   │       ├── pagination.py          # Pagination classes
│   │       ├── permissions.py         # API permissions (IsVerifiedEmail, etc.)
│   │       ├── throttling.py          # Rate limiting (auth, submission, report, search, messaging)
│   │       ├── middleware.py          # Admin IP whitelist, Axes lockout handler
│   │       ├── signals.py             # Signal handlers for admin notifications
│   │       ├── tasks.py               # Admin notifications + analytics cleanup tasks
│   │       ├── tests/
│   │       └── management/
│   │           └── commands/
│   │               ├── rebuild_search_vectors.py  # Rebuild full-text search indexes
│   │               └── setup_notifications.py     # Configure admin notification schedule
│   │
│   ├── templates/                     # Django templates
│   │   ├── admin/                     # Admin panel customization
│   │   │   ├── base_site.html
│   │   │   ├── index.html
│   │   │   ├── system_status.html     # System health dashboard
│   │   │   └── user_contributions.html # Bulk contribution review
│   │   ├── emails/                    # Email templates (inline CSS for Gmail)
│   │   │   ├── email_verification.html/.txt
│   │   │   ├── password_reset.html/.txt
│   │   │   ├── new_message.html/.txt        # New message notification
│   │   │   ├── strike_warning.html/.txt     # Community strike notice
│   │   │   ├── account_action.html/.txt     # Warning/restriction/suspension notice
│   │   │   ├── newsletter_confirm.html/.txt
│   │   │   ├── launch_announcement.html/.txt
│   │   │   └── admin/
│   │   │       ├── system_alert.html/.txt
│   │   │       ├── moderation_alert.html/.txt
│   │   │       └── activity_digest.html/.txt
│   │   ├── errors/
│   │   │   ├── 404.html
│   │   │   └── 500.html
│   │   └── base.html
│   │
│   └── utils/                         # Shared utilities
│       ├── __init__.py
│       ├── image_processing.py        # Image optimization
│       ├── email.py                   # Email helpers (templated, verification, reset, messages, strikes)
│       ├── content_filter.py          # Profanity/hate speech filter (regex + leet-speak normalization)
│       ├── file_validation.py         # Magic byte file type verification for uploads
│       ├── cache.py                   # Cache key helpers
│       └── validators.py              # Custom validators
│
├── frontend/                          # React frontend
│   ├── package.json                   # NPM dependencies
│   ├── package-lock.json
│   ├── vite.config.ts                 # Vite configuration
│   ├── tailwind.config.js             # Tailwind + cyberpunk theme
│   ├── tsconfig.json                  # TypeScript configuration
│   ├── .nvmrc                         # Node version (22)
│   ├── Dockerfile                     # Multi-stage frontend container
│   ├── nginx.conf                     # Nginx config for production
│   │
│   └── src/                           # Source code
│       ├── main.tsx                   # Application entry point
│       ├── App.tsx                    # Root component (routes, providers)
│       ├── index.css                  # Tailwind + cyberpunk CSS effects
│       │
│       ├── api/                       # API layer
│       │   ├── client.ts              # Axios instance + JWT cookie refresh
│       │   └── endpoints.ts           # All API endpoint functions (auth, products, components, messaging, reports, analytics, etc.)
│       │
│       ├── context/                   # React Context
│       │   └── AuthContext.tsx         # Auth state + JWT token management
│       │
│       ├── components/                # Reusable components
│       │   ├── layout/
│       │   │   ├── Header.tsx         # Nav bar + search dropdown + unread badge
│       │   │   ├── Footer.tsx         # Site footer + links
│       │   │   └── Layout.tsx         # Page wrapper
│       │   │
│       │   ├── moderation/
│       │   │   ├── ResolveReportModal.tsx  # Report resolution dialog
│       │   │   └── UserReviewPanel.tsx     # User review action panel
│       │   │
│       │   ├── PricingPanel.tsx       # Nexar pricing/availability display
│       │   ├── AddToJunkbinModal.tsx  # Modal for adding items to personal junkbin
│       │   ├── BadgeDisplay.tsx      # BadgeChip + BadgeGrid components for achievements
│       │   ├── AddComponentForm.tsx   # Link components to products
│       │   ├── GoogleLoginButton.tsx # Google OAuth sign-in button (GSI)
│       │   ├── BackToTop.tsx          # Floating scroll button
│       │   ├── BatchAddComponents.tsx # Bulk component linking
│       │   ├── BomImport.tsx          # BOM CSV file import
│       │   ├── BomTemplateDownload.tsx # BOM CSV template download
│       │   ├── ComponentVoteButtons.tsx # Confirm/dispute voting on cross-references
│       │   ├── ErrorBoundary.tsx      # React error boundary
│       │   ├── ImageUpload.tsx        # Drag & drop image upload
│       │   ├── KeyboardShortcutsModal.tsx # ? key help modal
│       │   ├── LazyImage.tsx          # Intersection observer lazy loading
│       │   ├── OnboardingTips.tsx     # Dismissable tips for new users
│       │   ├── Pagination.tsx         # Page navigation
│       │   ├── ProductComments.tsx    # Product comment thread + compose
│       │   ├── ReportModal.tsx        # Content/message reporting modal
│       │   ├── SchematicUpload.tsx    # Schematic file upload
│       │   ├── ScrollToTop.tsx        # Scroll to top on route change
│       │   └── Skeleton.tsx           # Loading placeholder
│       │
│       ├── pages/                     # Page components
│       │   ├── Home.tsx               # Landing page + newsletter signup
│       │   ├── Products.tsx           # Product listing + search/filter
│       │   ├── ProductDetail.tsx      # Product detail (images, components, schematics, voting)
│       │   ├── Components.tsx         # Component catalog
│       │   ├── ComponentDetail.tsx    # Cross-reference: products with component
│       │   ├── Schematics.tsx         # Schematic listing
│       │   ├── Search.tsx             # Global search with tabbed results
│       │   ├── Submit.tsx             # Multi-step product/component wizard
│       │   ├── MyJunkbin.tsx          # Personal collection manager (have/want tabs)
│       │   ├── Messages.tsx           # Inbox / conversation list
│       │   ├── MessageThread.tsx      # Conversation thread + compose
│       │   ├── NewConversation.tsx    # Start new conversation with user search
│       │   ├── UserProfile.tsx        # Public user profile page
│       │   ├── Guidelines.tsx         # Community guidelines
│       │   ├── Leaderboard.tsx        # User contribution rankings (clickable)
│       │   ├── Moderation.tsx         # Report/review moderation dashboard
│       │   ├── AnalyticsDashboard.tsx # Staff-only analytics (DAU, search, trending, activity)
│       │   ├── Recipes.tsx            # Recipe listing + search/filter
│       │   ├── RecipeDetail.tsx       # Recipe detail + BOM matching
│       │   ├── SubmitRecipe.tsx       # Recipe submission wizard
│       │   ├── Buildable.tsx          # "What Can I Build?" page
│       │   ├── Login.tsx              # Authentication
│       │   ├── Register.tsx           # User registration
│       │   ├── Profile.tsx            # User profile + stats
│       │   ├── VerifyEmail.tsx        # Email verification handler
│       │   ├── PasswordReset.tsx      # Password reset request
│       │   ├── PasswordResetConfirm.tsx # Password reset form
│       │   └── NotFound.tsx           # 404 page
│       │
│       ├── hooks/                     # Custom React hooks
│       │   ├── useKeyboardShortcuts.ts
│       │   ├── usePageVisibility.ts   # Page Visibility API wrapper
│       │   └── useUnreadCount.ts      # Adaptive polling for unread messages
│       │
│       ├── types/                     # TypeScript interfaces
│       │   ├── index.ts              # All shared types (Product, Component, Message, Analytics, etc.)
│       │   └── google.d.ts           # Google Identity Services type declarations
│       │
│       ├── test/                      # Test infrastructure
│       │   ├── setup.ts
│       │   ├── utils.tsx
│       │   └── mocks/
│       │       ├── handlers.ts        # MSW request handlers
│       │       └── server.ts          # MSW server setup
│       │
│       └── assets/
│           └── react.svg
│
├── deployment/                        # Deployment scripts & configs
│   ├── junkbin-deploy.sh              # Main deployment script
│   ├── update.sh                      # Quick update (pull + rebuild + migrate)
│   ├── backup.sh                      # Backup DB + media from Docker volume
│   ├── restore.sh                     # Restore from backup (interactive menu)
│   │
│   ├── nginx/                         # Nginx configurations
│   │   ├── nginx.conf                 # Main nginx config
│   │   └── sites-available/
│   │       ├── junkbin.conf           # Production (with SSL, Grafana/Prometheus proxy)
│   │       └── junkbin-local.conf     # Local dev (no SSL)
│   │
│   ├── prometheus/                    # Prometheus monitoring
│   │   └── prometheus.yml             # Scrape config (backend + nginx targets)
│   │
│   ├── grafana/                       # Grafana dashboards
│   │   ├── provisioning/
│   │   │   ├── datasources/
│   │   │   │   └── prometheus.yml     # Auto-provision Prometheus datasource
│   │   │   └── dashboards/
│   │   │       └── dashboard.yml      # Dashboard file provider config
│   │   └── dashboards/
│   │       └── junkbin-overview.json  # Pre-built overview dashboard (8 panels)
│   │
│   └── docker/                        # Docker-related files
│       └── postgres/
│           └── init.sql               # Initial DB setup
```

## File Naming Conventions

### Python (Backend)
- Snake_case for files and directories: `user_models.py`, `product_views.py`
- PascalCase for classes: `class ProductSerializer`
- Snake_case for functions/variables: `def get_user_profile()`

### TypeScript (Frontend)
- PascalCase for React components: `ProductDetail.tsx`
- camelCase for utilities/hooks: `useKeyboardShortcuts.ts`
- All React components use `.tsx`, non-JSX files use `.ts`

### General
- UPPERCASE for environment variables: `DATABASE_URL`, `SECRET_KEY`
- lowercase for directories: `products/`, `components/`

## Key Configuration Files

### Backend
- `config/settings/base.py` - Shared Django settings
- `config/settings/production.py` - Production overrides (DEBUG=False, etc.)
- `requirements.txt` - Python package dependencies

### Frontend
- `vite.config.ts` - Build configuration
- `package.json` - NPM dependencies and scripts
- `tailwind.config.js` - Cyberpunk theme colors/fonts

### Infrastructure
- `docker-compose.yml` - Multi-container definitions (9 services: backend, postgres, redis, celery, celery-beat, frontend, nginx, prometheus, grafana)
- `docker-compose.override.yml` - Local dev overrides (no SSL)
- `.env` - Environment variables (NOT committed to git)
- `deployment/nginx/sites-available/junkbin.conf` - Production web server config

## Environment Variables

See `.env.example` for required environment variables including:
- `SECRET_KEY` - Django secret key
- `DATABASE_URL` - PostgreSQL connection string
- `REDIS_URL` - Redis connection string
- `ALLOWED_HOSTS` - Allowed domain names
- `EMAIL_HOST` / `EMAIL_PORT` - SMTP configuration
- `OAUTH_GOOGLE_CLIENT_ID` / `OAUTH_GOOGLE_CLIENT_SECRET` - Google OAuth credentials (backend)
- `VITE_GOOGLE_CLIENT_ID` - Google OAuth client ID (frontend, public)
- `GRAFANA_ADMIN_PASSWORD` - Grafana admin password (default: admin)

---

**Last Updated**: February 15, 2026
