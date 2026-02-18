# Junkbin.io — Developer Guide

> Self-hosting, API reference, architecture overview, and contributing to the codebase.

---

## Table of Contents

- [Prerequisites](#prerequisites)
- [Quick Deploy (Automated)](#quick-deploy-automated)
- [Manual Setup (Docker Compose)](#manual-setup-docker-compose)
- [Environment Variables Reference](#environment-variables-reference)
- [Architecture Overview](#architecture-overview)
  - [Services](#services)
  - [Backend (Django)](#backend-django)
  - [Frontend (React)](#frontend-react)
  - [Database Schema](#database-schema)
- [API Reference](#api-reference)
  - [Authentication](#authentication)
  - [Core Endpoints](#core-endpoints)
  - [Rate Limits](#rate-limits)
- [Management Commands](#management-commands)
- [Running Tests](#running-tests)
- [Backup & Restore](#backup--restore)
- [Updating](#updating)
- [Monitoring](#monitoring)
- [Troubleshooting](#troubleshooting)
- [Contributing Code](#contributing-code)

---

## Prerequisites

### Server Requirements

| Requirement | Minimum | Recommended |
|-------------|---------|-------------|
| OS | Ubuntu 22.04, Debian 12, Fedora 39+, Arch, CentOS/RHEL 9+ | Ubuntu 24.04 LTS |
| RAM | 2 GB | 4 GB |
| Disk | 10 GB | 20 GB+ (for media) |
| Ports | 80, 443 | 80, 443, 3000 (Grafana), 9090 (Prometheus) |
| Domain | Required for SSL | — |

### Software (installed automatically by deploy script)

- Docker Engine 24+
- Docker Compose v2
- Git
- Certbot (for Let's Encrypt SSL)

---

## Quick Deploy (Automated)

The `junkbin-deploy.sh` script handles everything end-to-end:

```bash
git clone https://github.com/junkbin/junkbin.io.git
cd junkbin.io
sudo bash deployment/junkbin-deploy.sh
```

**What the script does:**

1. **Detects OS** — Ubuntu, Debian, Fedora, Arch, CentOS/RHEL, Alma, Rocky.
2. **Installs dependencies** — Docker, Docker Compose, Git, Certbot, system utilities.
3. **Configures firewall** — ufw (Debian/Ubuntu) or firewalld (RHEL/Fedora).
4. **Installs fail2ban** — SSH brute-force protection.
5. **Creates `.env`** — Generates secure random keys, prompts for domain/email/passwords.
6. **Builds & starts containers** — All 9 Docker services.
7. **Runs migrations** — Database schema setup.
8. **Creates superuser** — Admin account for Django admin.
9. **Sets up SSL** — Let's Encrypt certificate with auto-renewal.
10. **Seeds data** (optional) — Sample products and components.

---

## Manual Setup (Docker Compose)

For development or when you want full control:

```bash
# Clone
git clone https://github.com/junkbin/junkbin.io.git
cd junkbin.io

# Configure
cp .env.example .env
# Edit .env — at minimum set: SECRET_KEY, POSTGRES_PASSWORD, ALLOWED_HOSTS, SITE_URL

# Build & start
docker compose up -d --build

# Initialize database
docker compose exec backend python manage.py migrate
docker compose exec backend python manage.py createsuperuser
docker compose exec backend python manage.py collectstatic --noinput

# Seed sample data (optional)
docker compose exec backend python manage.py seed_data
docker compose exec backend python manage.py import_flipper_schematics
```

### Local Development (no SSL)

The default `docker-compose.yml` uses `deployment/nginx/sites-available/junkbin-local.conf` for local development (HTTP only). For production with SSL, the deploy script configures `junkbin.conf` with HTTPS.

### Frontend Development

The frontend is a multi-stage Docker build (Node.js build → Alpine with static files). For local frontend development with hot reload:

```bash
cd frontend
npm install
npm run dev
```

This starts Vite's dev server with HMR. Configure the API proxy in `vite.config.ts` to point to your backend.

---

## Environment Variables Reference

Copy `.env.example` to `.env` and configure. Key variables grouped by category:

### Django Core

| Variable | Default | Description |
|----------|---------|-------------|
| `SECRET_KEY` | — | **Required.** Django secret key. Generate a unique random string. |
| `DEBUG` | `False` | Set `True` for development only. |
| `ALLOWED_HOSTS` | `localhost` | Comma-separated hostnames (e.g., `junkbin.io,www.junkbin.io`). |

### Database

| Variable | Default | Description |
|----------|---------|-------------|
| `POSTGRES_DB` | `junkbin` | Database name. |
| `POSTGRES_USER` | `junkbin` | Database user. |
| `POSTGRES_PASSWORD` | — | **Required.** Database password. |
| `DATABASE_URL` | — | Full connection string (overrides individual vars). |

### Redis

| Variable | Default | Description |
|----------|---------|-------------|
| `REDIS_URL` | `redis://redis:6379/0` | Redis connection URL. |
| `REDIS_PASSWORD` | — | Redis password (set in redis config too). |

### Email (SMTP)

| Variable | Default | Description |
|----------|---------|-------------|
| `EMAIL_HOST` | — | SMTP server (e.g., `smtp.gmail.com`). |
| `EMAIL_PORT` | `587` | SMTP port. |
| `EMAIL_HOST_USER` | — | SMTP username. |
| `EMAIL_HOST_PASSWORD` | — | SMTP password or app password. |
| `EMAIL_USE_TLS` | `True` | Enable TLS. |
| `DEFAULT_FROM_EMAIL` | `noreply@junkbin.io` | Sender address. |

### OAuth

| Variable | Default | Description |
|----------|---------|-------------|
| `OAUTH_GOOGLE_CLIENT_ID` | — | Google OAuth client ID. |
| `OAUTH_GOOGLE_CLIENT_SECRET` | — | Google OAuth client secret. |

### Site

| Variable | Default | Description |
|----------|---------|-------------|
| `SITE_URL` | `http://localhost` | Full site URL with protocol. |
| `SITE_NAME` | `Junkbin.io` | Site display name. |
| `ADMIN_EMAIL` | — | Admin email for system notifications. |

### Security

| Variable | Default | Description |
|----------|---------|-------------|
| `CSRF_COOKIE_SECURE` | `True` | CSRF cookie requires HTTPS. |
| `SESSION_COOKIE_SECURE` | `True` | Session cookie requires HTTPS. |
| `CSP_UPGRADE_INSECURE` | `True` | CSP upgrade-insecure-requests. Set `False` for HTTP-only local dev. |
| `SECURE_HSTS_SECONDS` | `31536000` | HSTS max-age. |

### Rate Limiting

| Variable | Default | Description |
|----------|---------|-------------|
| `AUTH_RATE_LIMIT` | `5/min` | Auth endpoint limit. |
| `API_RATE_LIMIT` | `100/min` | General API limit. |
| `SEARCH_RATE_LIMIT` | `30/min` | Search endpoint limit. |
| `UPLOAD_RATE_LIMIT` | `10/min` | File upload limit. |

### External APIs

| Variable | Default | Description |
|----------|---------|-------------|
| `NEXAR_CLIENT_ID` | — | Nexar/Octopart API client ID. |
| `NEXAR_CLIENT_SECRET` | — | Nexar/Octopart API client secret. |

### Monitoring

| Variable | Default | Description |
|----------|---------|-------------|
| `GRAFANA_ADMIN_PASSWORD` | `admin` | Grafana dashboard password. |
| `SENTRY_DSN` | — | Sentry error tracking DSN. |

See `.env.example` for the complete list with inline documentation.

---

## Architecture Overview

### Services

The application runs as a Docker Compose stack with 9 services:

```
┌─────────────────────────────────────────────────┐
│                    nginx                         │
│              (reverse proxy)                     │
│  :80/:443 → backend, frontend, grafana, prom    │
└────┬──────────┬───────────┬──────────┬──────────┘
     │          │           │          │
┌────▼────┐ ┌──▼───┐ ┌────▼────┐ ┌───▼─────┐
│ backend │ │front-│ │ grafana │ │prometh- │
│ (Django)│ │ end  │ │ :3000   │ │ eus     │
│ :8000   │ │(static│ └────┬────┘ │ :9090   │
└────┬────┘ │files)│      │      └─────────┘
     │      └──────┘      │
┌────▼────┐          ┌────▼────┐
│  celery │          │postgres │
│ (worker)│          │  :5432  │
├─────────┤          └─────────┘
│  celery │          ┌─────────┐
│  (beat) │          │  redis  │
└─────────┘          │  :6379  │
                     └─────────┘
```

| Service | Image | Purpose |
|---------|-------|---------|
| `postgres` | postgres:15-alpine | PostgreSQL database |
| `redis` | redis:7-alpine | Cache, session store, Celery broker |
| `backend` | junkbinio-backend | Django API server (gunicorn) |
| `celery` | junkbinio-backend | Asynchronous task worker |
| `celery-beat` | junkbinio-backend | Periodic task scheduler |
| `frontend` | junkbinio-frontend | React static files (multi-stage build) |
| `nginx` | nginx:alpine | Reverse proxy, static files, SSL termination |
| `prometheus` | prom/prometheus | Metrics collection |
| `grafana` | grafana/grafana | Metrics dashboards |

### Backend (Django)

The backend is organized into 11 Django apps:

| App | Responsibility |
|-----|---------------|
| `users` | User model, profiles, reputation, badges, OAuth |
| `products` | Product CRUD, image uploads, view counting |
| `components` | Component CRUD, cross-reference, Nexar integration |
| `submissions` | Submission workflow, approval/rejection |
| `reports` | Content reporting, 3-strike system, user reviews |
| `messaging` | User-to-user conversations, blocking |
| `junkbin` | Have/want lists, want-matching notifications |
| `newsletter` | Launch email campaign |
| `recipes` | Community projects, BOM matching |
| `webhooks` | Discord/Slack webhook delivery |
| `api` | Search, analytics, health checks, Celery tasks |

See `docs/PROJECT_STRUCTURE.md` for the complete directory tree.

### Frontend (React)

- **Framework**: React 19 + TypeScript + Vite 7.3
- **Styling**: Tailwind CSS v3 with custom cyberpunk theme
- **State**: React Query 5.x for server state, Context API for auth
- **Routing**: React Router v6
- **Icons**: Lucide React
- **Testing**: Vitest + Testing Library + MSW (Mock Service Worker)

### Database Schema

Core models and their relationships:

```
User ─┬── Product (created_by)
      ├── Component (created_by)
      ├── ProductComponent (created_by)  ← junction table
      ├── Submission (submitted_by)
      ├── Report (reporter)
      ├── JunkbinItem (user)
      ├── Conversation / Message (sender)
      └── Recipe (created_by)

Product ──┬── ProductComponent ──── Component
          ├── Image
          ├── Schematic
          └── Comment

Recipe ──── RecipeComponent ──── Component
```

- **Product**: unique on `(manufacturer, model_number, revision, region)`, has slug.
- **Component**: unique on `(manufacturer, part_number)`, has computed `primary_value`.
- **ProductComponent**: junction with `reference_designator`, `quantity`, `location`.
- **JunkbinItem**: polymorphic via `ContentType` (can reference Product or Component).

---

## API Reference

Full interactive API documentation is available at `/api/docs/` (Swagger UI via drf-spectacular).

### Authentication

The API uses JWT with httpOnly cookies:

```bash
# Login — returns access + refresh tokens in cookies
curl -X POST /api/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "password": "..."}'

# Authenticated request
curl /api/products/ \
  -H "Authorization: Bearer <access_token>"

# Refresh token
curl -X POST /api/auth/refresh/

# Google OAuth
curl -X POST /api/auth/google/ \
  -H "Content-Type: application/json" \
  -d '{"credential": "<google_id_token>"}'
```

### Core Endpoints

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| `GET` | `/api/products/` | List products (paginated, filterable) | No |
| `POST` | `/api/products/` | Create product | Yes |
| `GET` | `/api/products/{id}/` | Product detail | No |
| `GET` | `/api/components/` | List components | No |
| `POST` | `/api/components/` | Create component | Yes |
| `GET` | `/api/components/{id}/` | Component detail | No |
| `GET` | `/api/components/{id}/products/` | Cross-reference | No |
| `GET` | `/api/schematics/` | List schematics | No |
| `GET` | `/api/search/` | Global search | No |
| `POST` | `/api/submissions/` | Submit content | Yes |
| `GET` | `/api/junkbin/` | Public junkbin items | No |
| `POST` | `/api/junkbin/` | Add to junkbin | Yes |
| `GET` | `/api/junkbin/my_items/` | User's junkbin | Yes |
| `GET` | `/api/recipes/` | List recipes | No |
| `POST` | `/api/reports/` | Submit report | Yes |
| `GET` | `/api/users/{id}/` | User profile | No |
| `GET` | `/api/stats/` | Platform statistics | No |
| `GET` | `/api/health/` | Health check | No |

### Rate Limits

Rate limit headers included in responses:

```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 97
X-RateLimit-Reset: 1708200000
```

Default limits (configurable via env vars):

| Endpoint Group | Default Limit |
|----------------|---------------|
| Auth (login, register) | 5/min |
| General API | 100/min |
| Search | 30/min |
| File uploads | 10/min |

---

## Management Commands

Run commands inside the backend container:

```bash
docker compose exec backend python manage.py <command>
```

| Command | App | Description |
|---------|-----|-------------|
| `seed_data [--flush]` | products | Seed 10 products, ~93 components, ~101 cross-references. `--flush` clears existing data first. |
| `import_flipper_schematics [--flush]` | products | Import 15 Flipper Zero schematic PDFs and datasheets. |
| `import_flipper_bom` | products | Import Flipper Zero BOM from Excel spreadsheet. |
| `backfill_badges` | users | Award badges to existing users who meet criteria. Run once after enabling badges. |
| `rebuild_search_vectors` | api | Rebuild PostgreSQL full-text search vectors and indexes. Run after bulk data imports. |
| `setup_notifications` | api | Configure the admin notification schedule. |
| `send_launch_email` | newsletter | Send launch announcement to all subscribers. |

### Standard Django Commands

```bash
# Database
docker compose exec backend python manage.py migrate
docker compose exec backend python manage.py makemigrations
docker compose exec backend python manage.py createsuperuser
docker compose exec backend python manage.py dbshell

# Static files
docker compose exec backend python manage.py collectstatic --noinput

# Shell
docker compose exec backend python manage.py shell_plus  # django-extensions

# Reset login lockouts (django-axes)
docker compose exec backend python manage.py axes_reset
```

---

## Running Tests

### Backend (pytest)

```bash
cd backend
DJANGO_SETTINGS_MODULE=config.settings.test pytest -v

# With coverage
pytest --cov=apps --cov-report=html
```

**Test coverage includes:**
- Users: reputation system, trusted promotion, permissions
- Reports: 3-strike system, resolution, user reviews
- Submissions: approval/rejection workflow, status transitions
- Products: slug generation, component counts, view counts
- Integration: full submission workflow, reputation flow

### Frontend (Vitest)

```bash
cd frontend
npm run test

# With coverage
npm run test:coverage
```

**Test coverage includes:**
- AuthContext: login, logout, token restoration
- API client: token refresh, authorization headers, retry
- Login/Register: form validation, error handling
- Components: AddComponentForm, ImageUpload, Submit wizard

---

## Backup & Restore

### Creating a Backup

```bash
# Production (Docker volumes)
sudo bash deployment/backup.sh

# Development (local database)
sudo bash deployment/backup.sh --dev
```

Backups include:
- PostgreSQL database dump (compressed)
- Media files from the Docker volume
- Stored in `backups/` with timestamp

### Restoring a Backup

```bash
sudo bash deployment/restore.sh
```

The interactive restore script:
1. Lists available backups.
2. Lets you choose which one to restore.
3. Supports selective restore (database only, media only, or both).

### Automated Backups

The deploy script configures a daily cron job at 2 AM:

```cron
0 2 * * * /path/to/junkbin.io/deployment/backup.sh
```

Backup retention: 30 days (older backups auto-cleaned).

---

## Updating

```bash
cd /path/to/junkbin.io
sudo bash deployment/update.sh
```

The update script:
1. Pulls latest code from git.
2. Rebuilds Docker images.
3. Runs database migrations.
4. Restarts all services.

For the frontend specifically (rebuild from scratch):

```bash
docker compose build frontend
docker compose down frontend nginx
docker volume rm junkbinio_frontend_build
docker compose up -d frontend nginx
```

---

## Monitoring

### Health Checks

- **Backend**: `GET /api/health/` — returns service status.
- **Nginx**: `GET /health` — returns 200 if nginx is running.
- **Docker**: Each service has a health check configured in `docker-compose.yml`.

### Prometheus & Grafana

- **Prometheus**: Available at `/prometheus/` (proxied through nginx). Scrapes backend and nginx metrics.
- **Grafana**: Available at `/grafana/`. Pre-provisioned dashboard with:
  - Request rate and latency percentiles
  - Error rate
  - Search volume
  - Component views
  - Submission activity
  - Database connection pool

Login: admin / `GRAFANA_ADMIN_PASSWORD` from `.env`.

### Admin Dashboard

Django admin includes a **System Status** page at `/admin/system-status/`:
- Service health (PostgreSQL, Redis, Celery workers, Celery Beat)
- CPU, memory, disk metrics
- Recent Celery task history
- Application statistics
- Quick links to admin tools

### Frontend Analytics

Staff users can access `/analytics` for:
- Daily active users
- Search analytics (top queries, zero-result queries)
- Trending components
- Content statistics
- Activity breakdown with date range selector (7d/30d/90d)

---

## Troubleshooting

### Common Issues

**"CSP blocks mixed content" in local dev**

Set `CSP_UPGRADE_INSECURE=False` in `.env` (the `upgrade-insecure-requests` CSP directive breaks HTTP-only development).

**Login lockout after failed attempts**

django-axes locks accounts after repeated failures. Reset with:
```bash
docker compose exec backend python manage.py axes_reset
```

**Environment variable changes not taking effect**

Docker Compose caches env vars. You must recreate containers:
```bash
docker compose up -d  # recreates, not just restarts
```
(`docker compose restart` does NOT pick up `.env` changes.)

**Media files not showing**

Media files live in the Docker named volume `media_files` at `/app/media` inside the container — not the bind-mounted `./backend/media` directory. To add files:
```bash
docker cp local_file.jpg junkbin-backend:/app/media/path/
```

**Frontend not updating after code changes**

The frontend uses a multi-stage Docker build. Rebuild from scratch:
```bash
docker compose build frontend
docker compose down frontend nginx
docker volume rm junkbinio_frontend_build
docker compose up -d frontend nginx
```

**PostgreSQL connection errors on re-deploy**

If the deploy script fails on PostgreSQL authentication, the init script may have run with different credentials. Either drop and recreate the database or update `deployment/docker/postgres/init.sql`.

**Search returning no results after bulk import**

Rebuild the full-text search indexes:
```bash
docker compose exec backend python manage.py rebuild_search_vectors
```

### Logs

```bash
# All services
docker compose logs -f

# Specific service
docker compose logs -f backend
docker compose logs -f celery
docker compose logs -f nginx

# Last 100 lines
docker compose logs --tail=100 backend
```

---

## Contributing Code

### Repository Structure

```
junkbin.io/
├── backend/          # Django project
│   ├── apps/         # 11 Django apps
│   ├── config/       # Settings, URLs, WSGI
│   └── templates/    # Email templates
├── frontend/         # React/Vite project
│   ├── src/
│   │   ├── pages/    # Route components
│   │   ├── components/  # Shared components
│   │   ├── hooks/    # Custom hooks
│   │   ├── context/  # React context
│   │   └── lib/      # API client, utilities
│   └── public/       # Static assets
├── deployment/       # Deploy scripts, nginx, monitoring
├── docs/             # Documentation
└── docker-compose.yml
```

See `docs/PROJECT_STRUCTURE.md` for the complete annotated directory tree.

### Development Workflow

1. **Fork** the repository.
2. **Create a feature branch** from `main`.
3. **Write tests** for new functionality.
4. **Ensure all tests pass** (backend and frontend).
5. **Submit a pull request** with a clear description of changes.

### Code Style

- **Python**: PEP 8, enforced by linter.
- **TypeScript/React**: ESLint configuration in `frontend/.eslintrc`.
- **CSS**: Tailwind utility classes. Custom styles in `frontend/src/index.css`.

### Naming Conventions

- **Python**: `snake_case` for variables/functions, `PascalCase` for classes.
- **TypeScript**: `camelCase` for variables/functions, `PascalCase` for components/types.
- **Files**: Python `snake_case.py`, TypeScript `PascalCase.tsx` for components.
- **URLs**: kebab-case (e.g., `/my-junkbin`).

---

*"They said 'NO USER SERVICEABLE PARTS INSIDE'... We took that personally."*

**Last Updated**: February 2026
