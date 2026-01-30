# Junkbin.io - Project Status Summary

**Location:** `/home/scap/junkbin.io`
**Last Updated:** 2026-01-29

---

## Current Status: MVP Nearly Complete

The core application is functional with all major frontend pages built and integrated with the backend API. The site features a cyberpunk "Coming Soon" landing page with live database statistics.

### Quick Start

```bash
# Terminal 1: Backend
cd /home/scap/junkbin.io
source venv/bin/activate
cd backend
DJANGO_SETTINGS_MODULE=config.settings.development python manage.py runserver 0.0.0.0:8000

# Terminal 2: Frontend
cd /home/scap/junkbin.io/frontend
source ~/.nvm/nvm.sh && nvm use 22
npm run dev -- --host 0.0.0.0 --port 3000
```

### Access Points
| URL | Description |
|-----|-------------|
| http://localhost:3000 | Frontend (React) |
| http://localhost:8000/api/ | Backend API |
| http://localhost:8000/api/docs/ | Swagger API Docs |
| http://localhost:8000/admin/ | Django Admin (admin / admin123) |

---

## Completed Features

### Backend (Django)
- [x] Django 5.x project with 6 apps (users, products, components, submissions, reports, api)
- [x] Full data models: User, Product, ProductImage, Schematic, Component, ProductComponent, Submission, Report, UserReview
- [x] 43 component types, 65 product categories, 11 regions
- [x] REST API with Django REST Framework
- [x] JWT authentication with token refresh
- [x] User registration and email verification setup
- [x] Google OAuth configuration (django-allauth)
- [x] Image upload with thumbnails (django-imagekit)
- [x] Schematic/document upload
- [x] Component cross-reference search
- [x] FCC ID field with external lookup links
- [x] 3-strike moderation system
- [x] Stats endpoint (`/api/stats/`) for live counts
- [x] Health check endpoint
- [x] Swagger/OpenAPI documentation (drf-spectacular)
- [x] Split settings (development/production/test)
- [x] Backup/restore scripts

### Frontend (React + Vite + TypeScript)
- [x] Vite 7.x with TypeScript
- [x] Tailwind CSS v3 with custom cyberpunk theme
- [x] React Query for data fetching
- [x] React Router v7 for navigation
- [x] JWT auth context with token refresh
- [x] Axios API client

### Frontend Pages
| Page | Route | Features |
|------|-------|----------|
| Home | `/` | Coming Soon landing, live stats, terminal UI, glitch effects |
| Products | `/products` | Search, filter by category, sort, grid/list view |
| Product Detail | `/products/:id` | Image gallery, components table, schematics, **image upload** |
| Components | `/components` | Search, filter by 43 types, sort, cross-reference links |
| Component Detail | `/components/:id/products` | Products containing component |
| Schematics | `/schematics` | Search, filter by type/source, download links |
| Submit | `/submit` | Multi-step forms for products & components |
| Profile | `/profile` | User stats, contributions, achievements |
| Login | `/login` | Cyberpunk styled auth |
| Register | `/register` | User registration |
| Search | `/search` | Global search with tabbed results (products, components, schematics) |
| 404 | `*` | Custom not found page |

### New Features (Jan 29, 2026)
- [x] **SchematicUpload component** - Upload schematics from ProductDetail page
- [x] **Global Search page** - `/search` with tabbed results for products/components/schematics
- [x] **Pagination** - Full pagination on Products, Components, Schematics pages
- [x] **AddComponentForm** - Link components to products directly from ProductDetail
- [x] **ReportModal** - Report issues with products/content for moderation
- [x] **Search Autocomplete** - Live search suggestions in header dropdown
- [x] **Mobile Responsive** - Tabs, tables, forms optimized for mobile
- [x] **Export Features** - JSON export + BOM CSV export from ProductDetail
- [x] **Lazy Loading** - LazyImage component for performance optimization
- [x] **Back to Top** - Floating button for long pages
- [x] **Skeleton Loading** - Loading placeholders for Products, Components pages

### Cyberpunk UI Features
- [x] Custom color palette (cyber-cyan, cyber-pink, cyber-green, cyber-yellow)
- [x] Neon glow effects on buttons and cards
- [x] Clip-path angled corners
- [x] Grid background pattern
- [x] **Glitch text animation** on titles
- [x] **Scanlines overlay** effect
- [x] **CRT flicker** on terminal elements
- [x] **Terminal-styled inputs** with glow
- [x] **Blinking cursor** animation
- [x] **Chromatic aberration** on hover
- [x] Custom scrollbar styling

### Image Upload System
- [x] Drag & drop interface
- [x] Multi-file selection
- [x] Preview before upload
- [x] Image type categorization (PCB front, back, closeup, label, etc.)
- [x] Caption field
- [x] Progress indicator
- [x] File validation (10MB max, images only)

### DevOps & Deployment
- [x] Node.js 22 via nvm (required for Vite 7)
- [x] `.nvmrc` file for version consistency
- [x] `junkbin-deploy.sh` - multi-distro deployment script
- [x] Automatic nvm/Node installation in deploy script
- [x] `backup.sh` and `restore.sh` scripts
- [x] Docker Compose configuration
- [x] Nginx configuration templates

---

## Remaining Tasks

### High Priority
| Task | Status | Notes |
|------|--------|-------|
| Schematic upload form | ✅ | Added to Product detail page schematics tab |
| Test full user flow | ⏳ | Register → Submit → Upload |

### Medium Priority
| Task | Status | Notes |
|------|--------|-------|
| Search functionality | ✅ | Global search page with tabbed results |
| Search autocomplete | ✅ | Header dropdown with live results |
| Pagination | ✅ | Products, components, schematics lists |
| Add components to products | ✅ | AddComponentForm in ProductDetail |
| Report content issues | ✅ | ReportModal with reason categories |
| Mobile responsive polish | ✅ | Tabs, tables, forms, search |
| Data export | ✅ | JSON + BOM CSV export |
| Image lazy loading | ✅ | LazyImage component |

### Low Priority (Production)
| Task | Status | Notes |
|------|--------|-------|
| PostgreSQL setup | ⏳ | Switch from SQLite |
| Redis/Celery setup | ⏳ | For background tasks |
| SSL/HTTPS | ⏳ | Let's Encrypt via deploy script |
| Production deployment | ⏳ | Run `junkbin-deploy.sh` |

---

## Tech Stack

### Backend
- Python 3.12
- Django 5.x
- Django REST Framework
- SimpleJWT (authentication)
- django-allauth (OAuth)
- django-imagekit (thumbnails)
- drf-spectacular (API docs)
- SQLite (dev) / PostgreSQL (prod)

### Frontend
- Node.js 22.x (via nvm)
- React 19
- Vite 7.3
- TypeScript 5.x
- Tailwind CSS 3.x
- React Query 5.x
- React Router 7.x
- Axios
- Lucide React (icons)

---

## Key Files

```
junkbin.io/
├── backend/
│   ├── apps/                    # Django apps
│   │   ├── api/                 # API root, stats, health
│   │   ├── users/               # Custom user model
│   │   ├── products/            # Products, images, schematics
│   │   ├── components/          # Component database
│   │   ├── submissions/         # Submission workflow
│   │   └── reports/             # Moderation system
│   ├── config/settings/         # Split settings
│   ├── templates/               # Email & error templates
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── api/                 # API client & endpoints
│   │   ├── components/          # Reusable components
│   │   │   ├── layout/          # Header, Footer, Layout
│   │   │   ├── ImageUpload.tsx  # Image upload component
│   │   │   ├── SchematicUpload.tsx # Schematic upload component
│   │   │   ├── AddComponentForm.tsx # Link components to products
│   │   │   ├── ReportModal.tsx  # Content reporting modal
│   │   │   ├── Pagination.tsx   # Reusable pagination
│   │   │   ├── Skeleton.tsx     # Loading skeletons
│   │   │   ├── LazyImage.tsx    # Lazy loading images
│   │   │   └── BackToTop.tsx    # Scroll to top button
│   │   ├── context/             # Auth context
│   │   ├── pages/               # All page components
│   │   ├── types/               # TypeScript interfaces
│   │   └── index.css            # Tailwind + cyberpunk effects
│   ├── .nvmrc                   # Node version (22)
│   └── REQUIREMENTS.md          # Frontend requirements
├── deployment/
│   ├── junkbin-deploy.sh        # Main deployment script
│   ├── backup.sh
│   └── restore.sh
├── docs/
│   └── ROADMAP.md               # Full project roadmap
└── projectsummary.md            # This file
```

---

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/` | GET | API root |
| `/api/stats/` | GET | Live database counts |
| `/api/health/` | GET | Health check |
| `/api/auth/token/` | POST | JWT login |
| `/api/auth/token/refresh/` | POST | Refresh token |
| `/api/auth/register/` | POST | User registration |
| `/api/auth/me/` | GET | Current user |
| `/api/products/` | GET, POST | Products list/create |
| `/api/products/{id}/` | GET, PATCH | Product detail |
| `/api/products/{id}/upload_image/` | POST | Upload image |
| `/api/products/{id}/upload_schematic/` | POST | Upload schematic |
| `/api/products/{id}/components/` | GET | Product's components |
| `/api/products/{id}/schematics/` | GET | Product's schematics |
| `/api/components/` | GET, POST | Components list/create |
| `/api/components/{id}/` | GET | Component detail |
| `/api/components/{id}/cross_reference/` | GET | Products with component |
| `/api/schematics/` | GET | Schematics list |
| `/api/search/` | GET | Global search |

---

## Color Reference

```css
/* Backgrounds */
--cyber-black:  #0a0a0f
--cyber-darker: #0d0d14
--cyber-dark:   #12121a
--cyber-gray:   #1a1a24
--cyber-light:  #2a2a3a

/* Neon Accents */
--cyber-cyan:   #05d9e8   /* Primary - Products */
--cyber-pink:   #ff2a6d   /* Secondary - Components */
--cyber-green:  #39ff14   /* Tertiary - Schematics */
--cyber-yellow: #f9f002   /* Warning/Featured */
```

---

*"NO USER SERVICEABLE PARTS INSIDE" — We took that personally.*
