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
│   ├── requirements.txt               # Python dependencies
│   ├── Dockerfile                     # Backend container image
│   ├── .dockerignore                  # Docker ignore rules
│   │
│   ├── config/                        # Django project configuration
│   │   ├── __init__.py
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
│   │   │   ├── models.py              # Custom User model
│   │   │   ├── views.py               # Authentication views
│   │   │   ├── serializers.py         # API serializers
│   │   │   ├── urls.py                # User-specific routes
│   │   │   ├── admin.py               # Admin configuration
│   │   │   ├── authentication.py      # JWT cookie auth backend
│   │   │   ├── permissions.py         # IsOwnerOrReadOnly, IsModerator, IsTrustedUser
│   │   │   ├── signals.py             # User-related signals
│   │   │   └── tests/
│   │   │
│   │   ├── products/                  # Product management
│   │   │   ├── models.py              # Product, ProductImage, Schematic
│   │   │   ├── views.py               # Product CRUD views
│   │   │   ├── serializers.py         # Product serializers
│   │   │   ├── urls.py                # Product routes
│   │   │   ├── admin.py               # Product admin + CSV export
│   │   │   ├── filters.py             # Search filters
│   │   │   ├── tests/
│   │   │   └── management/
│   │   │       └── commands/
│   │   │           ├── seed_data.py             # 10 products, ~93 components, ~101 cross-refs
│   │   │           ├── import_flipper_schematics.py  # 15 Flipper Zero PDFs + datasheets
│   │   │           └── import_flipper_bom.py    # Flipper Zero BOM from Excel
│   │   │
│   │   ├── components/                # Component management
│   │   │   ├── models.py              # Component, ProductComponent
│   │   │   ├── views.py               # Component CRUD + cross-reference
│   │   │   ├── serializers.py
│   │   │   ├── urls.py
│   │   │   ├── admin.py               # Component admin + CSV export
│   │   │   ├── filters.py             # Component search filters
│   │   │   └── tests/
│   │   │
│   │   ├── submissions/               # Content submission/moderation
│   │   │   ├── models.py              # Submission model
│   │   │   ├── views.py               # Submission workflow
│   │   │   ├── serializers.py
│   │   │   ├── urls.py
│   │   │   ├── admin.py
│   │   │   ├── tasks.py               # Celery tasks
│   │   │   └── tests/
│   │   │
│   │   ├── reports/                   # User reporting system
│   │   │   ├── models.py              # Report, UserReview models
│   │   │   ├── views.py               # Report handling
│   │   │   ├── serializers.py
│   │   │   ├── urls.py
│   │   │   ├── admin.py
│   │   │   ├── signals.py             # Auto-trigger on 3 strikes
│   │   │   └── tests/
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
│   │   └── api/                       # API configuration
│   │       ├── urls.py                # API root routing
│   │       ├── routers.py             # DRF routers
│   │       ├── pagination.py          # Pagination classes
│   │       ├── permissions.py         # API permissions
│   │       └── throttling.py          # Rate limiting
│   │
│   ├── templates/                     # Django templates
│   │   ├── emails/                    # Email templates (inline CSS for Gmail)
│   │   │   ├── verification.html
│   │   │   ├── email_verification.html
│   │   │   ├── password_reset.html
│   │   │   ├── newsletter_confirm.html  # Subscribe confirmation
│   │   │   ├── newsletter_confirm.txt
│   │   │   ├── launch_announcement.html # Launch blast email
│   │   │   └── launch_announcement.txt
│   │   └── errors/
│   │       ├── 404.html
│   │       └── 500.html
│   │
│   └── utils/                         # Shared utilities
│       ├── __init__.py
│       ├── image_processing.py        # Image optimization
│       ├── email.py                   # Email helpers (send_templated_email)
│       └── validators.py              # Custom validators
│
├── frontend/                          # React frontend
│   ├── package.json                   # NPM dependencies
│   ├── package-lock.json
│   ├── vite.config.js                 # Vite configuration
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
│       │   ├── client.ts              # Axios instance + token refresh
│       │   └── endpoints.ts           # All API endpoint functions
│       │
│       ├── context/                   # React Context
│       │   └── AuthContext.tsx         # Auth state + JWT token management
│       │
│       ├── components/                # Reusable components
│       │   ├── layout/
│       │   │   ├── Header.tsx         # Nav bar + search dropdown
│       │   │   ├── Footer.tsx
│       │   │   └── Layout.tsx         # Page wrapper
│       │   │
│       │   ├── AddComponentForm.tsx   # Link components to products
│       │   ├── BackToTop.tsx          # Floating scroll button
│       │   ├── BomTemplateDownload.tsx # BOM CSV template download
│       │   ├── ErrorBoundary.tsx      # React error boundary
│       │   ├── ImageUpload.tsx        # Drag & drop image upload
│       │   ├── KeyboardShortcutsModal.tsx # ? key help modal
│       │   ├── LazyImage.tsx          # Intersection observer lazy loading
│       │   ├── OnboardingTips.tsx     # Dismissable tips for new users
│       │   ├── Pagination.tsx         # Page navigation
│       │   ├── ReportModal.tsx        # Content reporting modal
│       │   ├── SchematicUpload.tsx    # Schematic file upload
│       │   ├── ScrollToTop.tsx        # Scroll to top on route change
│       │   └── Skeleton.tsx           # Loading placeholder
│       │
│       ├── pages/                     # Page components
│       │   ├── Home.tsx               # Landing page + newsletter signup
│       │   ├── Products.tsx           # Product listing + search/filter
│       │   ├── ProductDetail.tsx      # Product detail (images, components, schematics)
│       │   ├── Components.tsx         # Component catalog
│       │   ├── ComponentDetail.tsx    # Cross-reference: products with component
│       │   ├── Schematics.tsx         # Schematic listing
│       │   ├── Search.tsx             # Global search with tabbed results
│       │   ├── Submit.tsx             # Multi-step product/component wizard
│       │   ├── Login.tsx              # Authentication
│       │   ├── Register.tsx           # User registration
│       │   ├── Profile.tsx            # User profile + stats
│       │   ├── VerifyEmail.tsx        # Email verification handler
│       │   ├── PasswordReset.tsx      # Password reset request
│       │   ├── PasswordResetConfirm.tsx # Password reset form
│       │   └── NotFound.tsx           # 404 page
│       │
│       ├── hooks/                     # Custom React hooks
│       │   └── useKeyboardShortcuts.ts
│       │
│       ├── types/                     # TypeScript interfaces
│       │   └── index.ts
│       │
│       ├── __tests__/                 # Test infrastructure
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
│   │   └── sites-available/
│   │       ├── junkbin.conf           # Production (with SSL)
│   │       └── junkbin-local.conf     # Local dev (no SSL)
│   │
│   ├── docker/                        # Docker-related files
│   │   └── postgres/
│   │       └── init.sql               # Initial DB setup
│   │
│   └── systemd/                       # Systemd service files
│       ├── junkbin.service
│       └── junkbin-celery.service
│
└── tests/                             # Integration/E2E tests
    └── conftest.py                    # Pytest configuration
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
- `vite.config.js` - Build configuration
- `package.json` - NPM dependencies and scripts
- `tailwind.config.js` - Cyberpunk theme colors/fonts

### Infrastructure
- `docker-compose.yml` - Multi-container definitions
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
- `OAUTH_GOOGLE_CLIENT_ID` / `OAUTH_GOOGLE_CLIENT_SECRET` - OAuth credentials

---

**Last Updated**: February 11, 2026
