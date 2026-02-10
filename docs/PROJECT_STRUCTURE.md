# Junkbin.io - Project Structure

```
junkbin.io/
├── README.md                          # Project overview
├── LICENSE                            # MIT License
├── .gitignore                         # Git ignore rules
├── docker-compose.yml                 # Multi-container orchestration
├── .env.example                       # Environment variables template
│
├── docs/                              # Documentation
│   ├── ROADMAP.md                     # Project roadmap (this document)
│   ├── API.md                         # API documentation
│   ├── CONTRIBUTING.md                # Contribution guidelines
│   ├── DEPLOYMENT.md                  # Production deployment guide
│   ├── USER_GUIDE.md                  # End-user documentation
│   ├── SECURITY.md                    # Security policy
│   └── CHANGELOG.md                   # Version history
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
│   │   └── asgi.py                    # ASGI application (future WebSockets)
│   │
│   ├── apps/                          # Django applications
│   │   │
│   │   ├── users/                     # User management
│   │   │   ├── __init__.py
│   │   │   ├── models.py              # User, Profile models
│   │   │   ├── views.py               # Authentication views
│   │   │   ├── serializers.py         # API serializers
│   │   │   ├── urls.py                # User-specific routes
│   │   │   ├── admin.py               # Admin configuration
│   │   │   ├── signals.py             # User-related signals
│   │   │   ├── permissions.py         # Custom permissions
│   │   │   └── tests/                 # User tests
│   │   │
│   │   ├── products/                  # Product management
│   │   │   ├── __init__.py
│   │   │   ├── models.py              # Product, Image models
│   │   │   ├── views.py               # Product CRUD views
│   │   │   ├── serializers.py         # Product serializers
│   │   │   ├── urls.py                # Product routes
│   │   │   ├── admin.py               # Product admin
│   │   │   ├── filters.py             # Search filters
│   │   │   ├── validators.py          # Image/data validators
│   │   │   └── tests/
│   │   │
│   │   ├── components/                # Component management
│   │   │   ├── __init__.py
│   │   │   ├── models.py              # Component, ProductComponent
│   │   │   ├── views.py               # Component CRUD
│   │   │   ├── serializers.py
│   │   │   ├── urls.py
│   │   │   ├── admin.py
│   │   │   ├── search.py              # Component search logic
│   │   │   └── tests/
│   │   │
│   │   ├── submissions/               # Content submission/moderation
│   │   │   ├── __init__.py
│   │   │   ├── models.py              # Submission, Review models
│   │   │   ├── views.py               # Submission workflow
│   │   │   ├── serializers.py
│   │   │   ├── urls.py
│   │   │   ├── admin.py
│   │   │   ├── tasks.py               # Celery tasks
│   │   │   └── tests/
│   │   │
│   │   ├── reports/                   # User reporting system
│   │   │   ├── __init__.py
│   │   │   ├── models.py              # Report, UserReview models
│   │   │   ├── views.py               # Report handling
│   │   │   ├── serializers.py
│   │   │   ├── urls.py
│   │   │   ├── admin.py
│   │   │   ├── signals.py             # Auto-trigger on 3 strikes
│   │   │   └── tests/
│   │   │
│   │   ├── newsletter/                 # Newsletter / email collection
│   │   │   ├── __init__.py
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
│   │       ├── __init__.py
│   │       ├── urls.py                # API root routing
│   │       ├── routers.py             # DRF routers
│   │       ├── pagination.py          # Pagination classes
│   │       ├── permissions.py         # API permissions
│   │       └── throttling.py          # Rate limiting
│   │
│   ├── static/                        # Static files (CSS, JS, images)
│   │   ├── admin/                     # Django admin overrides
│   │   ├── css/
│   │   └── images/
│   │
│   ├── media/                         # User-uploaded files
│   │   ├── products/                  # Product images
│   │   ├── components/                # Component images
│   │   └── temp/                      # Temporary uploads
│   │
│   ├── templates/                     # Django templates
│   │   ├── base.html
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
│       ├── email.py                   # Email helpers
│       └── validators.py              # Custom validators
│
├── frontend/                          # React frontend
│   ├── package.json                   # NPM dependencies
│   ├── package-lock.json
│   ├── vite.config.js                 # Vite configuration
│   ├── .eslintrc.json                 # ESLint configuration
│   ├── .prettierrc                    # Prettier configuration
│   ├── Dockerfile                     # Frontend container
│   ├── nginx.conf                     # Nginx config for production
│   │
│   ├── public/                        # Static assets
│   │   ├── favicon.ico
│   │   ├── robots.txt
│   │   └── manifest.json              # PWA manifest
│   │
│   ├── src/                           # Source code
│   │   ├── main.jsx                   # Application entry point
│   │   ├── App.jsx                    # Root component
│   │   │
│   │   ├── components/                # Reusable components
│   │   │   ├── common/
│   │   │   │   ├── Button.jsx
│   │   │   │   ├── Input.jsx
│   │   │   │   ├── Modal.jsx
│   │   │   │   ├── ImageGallery.jsx
│   │   │   │   └── Loading.jsx
│   │   │   │
│   │   │   ├── layout/
│   │   │   │   ├── Header.jsx
│   │   │   │   ├── Footer.jsx
│   │   │   │   ├── Sidebar.jsx
│   │   │   │   └── Navigation.jsx
│   │   │   │
│   │   │   ├── products/
│   │   │   │   ├── ProductCard.jsx
│   │   │   │   ├── ProductList.jsx
│   │   │   │   ├── ProductDetail.jsx
│   │   │   │   └── ProductForm.jsx
│   │   │   │
│   │   │   ├── components/
│   │   │   │   ├── ComponentCard.jsx
│   │   │   │   ├── ComponentSearch.jsx
│   │   │   │   └── ComponentDetail.jsx
│   │   │   │
│   │   │   └── admin/
│   │   │       ├── ModerationQueue.jsx
│   │   │       ├── UserReview.jsx
│   │   │       └── Analytics.jsx
│   │   │
│   │   ├── pages/                     # Page components
│   │   │   ├── Home.jsx
│   │   │   ├── Login.jsx
│   │   │   ├── Register.jsx
│   │   │   ├── ProductsPage.jsx
│   │   │   ├── ProductDetailPage.jsx
│   │   │   ├── SearchPage.jsx
│   │   │   ├── SubmitPage.jsx
│   │   │   ├── ProfilePage.jsx
│   │   │   ├── AdminDashboard.jsx
│   │   │   ├── About.jsx
│   │   │   └── NotFound.jsx
│   │   │
│   │   ├── hooks/                     # Custom React hooks
│   │   │   ├── useAuth.js
│   │   │   ├── useProducts.js
│   │   │   ├── useComponents.js
│   │   │   └── useSearch.js
│   │   │
│   │   ├── services/                  # API services
│   │   │   ├── api.js                 # Axios instance
│   │   │   ├── auth.js                # Auth API calls
│   │   │   ├── products.js            # Product API calls
│   │   │   ├── components.js          # Component API calls
│   │   │   └── submissions.js         # Submission API calls
│   │   │
│   │   ├── context/                   # React Context
│   │   │   ├── AuthContext.jsx
│   │   │   └── ThemeContext.jsx
│   │   │
│   │   ├── utils/                     # Utility functions
│   │   │   ├── validation.js
│   │   │   ├── formatting.js
│   │   │   └── constants.js
│   │   │
│   │   ├── styles/                    # CSS/styling
│   │   │   ├── index.css              # Global styles
│   │   │   ├── theme.js               # Cyberpunk theme
│   │   │   └── animations.css         # Glitch effects, etc.
│   │   │
│   │   └── assets/                    # Images, fonts, etc.
│   │       ├── images/
│   │       ├── fonts/
│   │       └── icons/
│   │
│   └── tests/                         # Frontend tests
│       ├── unit/
│       └── integration/
│
├── deployment/                        # Deployment scripts & configs
│   ├── junkbin-deploy.sh              # Main deployment script
│   ├── update.sh                      # Update script
│   ├── backup.sh                      # Backup script (--dev for non-Docker)
│   ├── restore.sh                     # Restore script (--dev for non-Docker)
│   │
│   ├── nginx/                         # Nginx configurations
│   │   ├── nginx.conf                 # Main config
│   │   ├── sites-available/
│   │   │   └── junkbin.conf           # Site-specific config
│   │   └── ssl/                       # SSL configuration
│   │       └── options-ssl-nginx.conf
│   │
│   ├── docker/                        # Docker-related files
│   │   ├── postgres/
│   │   │   └── init.sql               # Initial DB setup
│   │   └── redis/
│   │       └── redis.conf             # Redis configuration
│   │
│   ├── systemd/                       # Systemd service files
│   │   ├── junkbin.service
│   │   └── junkbin-celery.service
│   │
│   └── monitoring/                    # Monitoring configs
│       ├── prometheus.yml
│       └── grafana/
│           └── dashboards/
│
├── scripts/                           # Utility scripts
│   ├── seed_database.py               # Seed initial data
│   ├── import_csv.py                  # CSV import tool
│   ├── export_data.py                 # Data export
│   ├── cleanup_images.py              # Remove orphaned images
│   └── user_stats.py                  # Generate user statistics
│
└── tests/                             # Integration/E2E tests
    ├── conftest.py                    # Pytest configuration
    ├── test_api.py                    # API integration tests
    ├── test_workflows.py              # User workflow tests
    └── test_performance.py            # Performance tests
```

## File Naming Conventions

### Python (Backend)
- Snake_case for files and directories: `user_models.py`, `product_views.py`
- PascalCase for classes: `class ProductSerializer`
- Snake_case for functions/variables: `def get_user_profile()`

### JavaScript (Frontend)
- PascalCase for React components: `ProductCard.jsx`
- camelCase for utilities/services: `authService.js`
- kebab-case for CSS files: `component-styles.css`

### General
- UPPERCASE for environment variables: `DATABASE_URL`, `SECRET_KEY`
- lowercase for directories: `products/`, `components/`
- Descriptive names over abbreviations: `authentication.py` not `auth.py` (unless very common)

## Key Configuration Files

### Backend
- `config/settings/base.py` - Shared Django settings
- `config/settings/production.py` - Production overrides (DEBUG=False, etc.)
- `requirements.txt` - Python package dependencies

### Frontend
- `vite.config.js` - Build configuration
- `package.json` - NPM dependencies and scripts
- `src/styles/theme.js` - Cyberpunk theme colors/fonts

### Infrastructure
- `docker-compose.yml` - Multi-container definitions
- `.env` - Environment variables (NOT committed to git)
- `deployment/nginx/nginx.conf` - Web server configuration

## Environment Variables

See `.env.example` for required environment variables including:
- `SECRET_KEY` - Django secret key
- `DATABASE_URL` - PostgreSQL connection string
- `REDIS_URL` - Redis connection string
- `ALLOWED_HOSTS` - Allowed domain names
- `EMAIL_HOST` / `EMAIL_PORT` - SMTP configuration
- `OAUTH_GOOGLE_CLIENT_ID` / `OAUTH_GOOGLE_CLIENT_SECRET` - OAuth credentials
- `STORAGE_BACKEND` - 'local' or 's3'
- `AWS_STORAGE_BUCKET_NAME` - S3 bucket (if using S3)

---

**Last Updated**: February 2026
