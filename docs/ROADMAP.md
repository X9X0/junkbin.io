# Junkbin.io - Project Roadmap
## "NO USER SERVICEABLE PARTS INSIDE" - The E-Waste Salvage Database

---

## Project Vision

A community-driven database documenting electronic components found in consumer electronics, transforming e-waste into a searchable parts catalog for repair and salvage purposes. Think Wikipedia meets Octopart for teardown documentation.

---

## Core Concept

Users document components inside consumer electronics by posting:
- Make, model, revision, region
- High-quality PCB photos
- Bill of materials (BOM)
- Component locations and reference designators

Other users can search this database to find which consumer products contain specific components they need for repairs.

---

## Tech Stack

### Backend
- **Framework**: Django 5.x (Python 3.11+)
  - Built-in admin panel
  - Django REST Framework for API
  - Django-allauth for OAuth/SSO
  - Django-moderation for content review
- **Database**: PostgreSQL 15+
  - Full-text search capabilities
  - JSONB for flexible component metadata
  - PostGIS for potential future geolocation features
- **Cache/Queue**: Redis 7+
  - Session management
  - Celery task queue
  - Search result caching
- **Task Queue**: Celery
  - Email verification
  - Image processing and thumbnail generation
  - Periodic cleanup tasks
  - Report aggregation

### Frontend
- **Framework**: React 19 with Vite 7.3 (Node.js 22 via nvm)
- **UI Library**: Custom components with Lucide React icons
- **Styling**: Tailwind CSS v3 with custom cyberpunk theme
- **State Management**: React Query 5.x + Context API (AuthContext)
- **Image Handling**: Custom ImageUpload component with drag & drop

### Infrastructure
- **Containerization**: Docker + Docker Compose
- **Web Server**: Nginx (reverse proxy, static file serving)
- **SSL/TLS**: Let's Encrypt with certbot
- **Storage**: 
  - Local filesystem (development)
  - MinIO or AWS S3 (production)
- **Backup**: Automated PostgreSQL dumps + file storage sync
- **Monitoring**:
  - Prometheus + Grafana (future)
  - Health check endpoints (`/api/health/`, nginx `/health`)
  - Admin system status dashboard (service health, metrics, Celery tasks)

### Deployment Targets
- Ubuntu 22.04/24.04 LTS
- Fedora 39+
- Arch Linux
- Debian 12+
- Any systemd-based Linux distribution

---

## Database Schema

### Core Tables

#### 1. Users (Extended Django User)
```
- id (UUID)
- username
- email
- email_verified
- oauth_provider (google, github, microsoft, null)
- reputation_score (calculated)
- contribution_count
- report_count (times user's content was reported)
- review_count (times user's content triggered review)
- is_trusted (boolean, earned status)
- created_at
- last_login
```

#### 2. Products
```
- id (UUID)
- manufacturer
- model_number
- revision (optional)
- region (US, EU, JP, etc.)
- category (TV, Router, Phone, etc.)
- year_manufactured (optional)
- fcc_id (optional)
- description (text)
- primary_image (reference)
- created_at
- updated_at
- created_by (User FK)
```

#### 3. Components
```
- id (UUID)
- part_number (indexed)
- manufacturer
- component_type (IC, FET, Resistor, Capacitor, Module, etc.)
- package_type (SOT-23, SOIC-8, 0805, etc.)
- description
- datasheet_url
- typical_function (voltage regulator, MCU, etc.)
- created_at
- updated_at
- created_by (User FK)
```

#### 4. ProductComponents (Junction Table)
```
- id (UUID)
- product_id (FK)
- component_id (FK)
- reference_designator (U1, R5, C12, etc.)
- quantity
- location_description (near HDMI port, on power board, etc.)
- notes
- image_reference (which image shows this component)
- submission_level (basic, advanced)
- created_at
- created_by (User FK)
```

#### 5. Images
```
- id (UUID)
- product_id (FK)
- file_path
- thumbnail_path
- image_type (overview, closeup, backside, schematic)
- caption
- uploaded_at
- uploaded_by (User FK)
```

#### 6. Submissions
```
- id (UUID)
- product_id (FK)
- submission_type (new_product, update_existing, component_addition)
- submission_level (basic, advanced)
- status (pending, approved, rejected)
- submitted_at
- submitted_by (User FK)
- reviewed_at
- reviewed_by (User FK, nullable)
- review_notes
```

#### 7. Reports
```
- id (UUID)
- reported_item_type (product, component, product_component)
- reported_item_id (UUID)
- reporter (User FK)
- reason (incorrect_info, duplicate, spam, other)
- description
- status (pending, investigating, resolved, dismissed)
- created_at
- resolved_at
- resolved_by (User FK, nullable)
- resolution_notes
```

#### 8. UserReviews
```
- id (UUID)
- user_id (FK to user being reviewed)
- triggered_by (report_id FK)
- review_type (manual, automatic_threshold)
- status (pending, cleared, sanctioned)
- created_at
- reviewed_at
- reviewer_id (User FK)
- notes
```

---

## Feature Breakdown

### Phase 1: MVP (Weeks 1-6) ✅ COMPLETE

#### Week 1-2: Infrastructure & Backend Foundation
- ✅ Set up development environment
- ✅ Create Django project structure
- ✅ Configure PostgreSQL database (SQLite for dev, PostgreSQL ready for prod)
- ✅ Implement core models (User, Product, Component, ProductComponent)
- ✅ Set up Django admin interface
- ✅ Create database migrations
- ✅ Implement basic API endpoints (CRUD for products)
- ✅ Set up Redis and Celery (running in Docker Compose stack)
- ✅ Configure email backend

#### Week 2-3: Authentication & User Management
- ✅ Implement email/password registration
- ✅ Email verification workflow
- ✅ Google OAuth integration (django-allauth configured)
- ✅ Basic user profile pages
- ✅ Password reset functionality
- ✅ Session management (JWT with refresh tokens)

#### Week 3-4: Core Submission Features
- ✅ Product submission form (backend)
- ✅ Image upload handling (with thumbnails via django-imagekit)
- ✅ Basic/Advanced submission levels
- ✅ Component search functionality
- ✅ Product-component linking
- ✅ Reference designator tracking

#### Week 4-5: Frontend Development
- ✅ React project setup with Vite (Vite 7.3 + Node 22)
- ✅ Cyberpunk dark theme implementation (custom Tailwind theme)
- ✅ "NO USER SERVICEABLE PARTS INSIDE" Easter eggs
- ✅ Product listing page (search, filter, grid/list view)
- ✅ Product detail page (gallery, components, schematics, image upload)
- ✅ Component search interface (43 component types, cross-reference)
- ✅ Submission form UI (multi-step wizard)
- ✅ Image gallery with zoom (basic gallery implemented)

#### Week 5-6: Admin & Moderation
- ✅ Admin dashboard for content review (Django admin)
- ⬜ Bulk user contribution review tools
- ✅ Basic moderation queue
- ✅ User contribution statistics
- ✅ Simple report system (3-strike moderation)

### Phase 2: Enhanced Features (Weeks 7-14) 🔄 IN PROGRESS

#### Week 7-8: Advanced Search & Filtering
- ✅ Multi-parameter search (products, components, schematics)
- ✅ Filter by manufacturer, category, region
- ✅ Component cross-reference search
- ✅ "Find products containing component X"
- ✅ Search result caching (Redis `cache_page` on list/search/stats endpoints)
- ✅ Search suggestions/autocomplete (header dropdown with live results)

#### Week 9-10: Reporting & Moderation System
- ✅ User report submission form (ReportModal component)
- ✅ Report review workflow (frontend moderation dashboard at /moderation)
- ✅ 3-strike automatic review trigger
- ✅ User reputation system (contribution_count, is_trusted)
- ⬜ Badge/achievement system
- ✅ Trusted user status

#### Week 10-11: Data Import/Export
- ✅ CSV BOM import with column mapping — 3-step wizard (upload, column mapping with auto-detect, preview/import), dry-run support, 61 header aliases, component type auto-classification (Feb 13, 2026)
- ✅ BOM template downloads (CSV template + instructions)
- ✅ API for programmatic access (REST API complete)
- ✅ Export product data as CSV/JSON (JSON + BOM CSV export)
- ✅ **Flipper Zero BOM import command** - `manage.py import_flipper_bom` imports ~93 components with reference designators from Excel BOM (Feb 11, 2026)
- ✅ Batch component addition — multi-row inline form with paste-from-clipboard support, auto-detect component type/package (Feb 13, 2026)

##### CSV BOM Import — Implementation Notes

**Overview:** Allow users to upload a CSV bill-of-materials and bulk-import components
linked to a product. Available on both the frontend (product detail page) and Django admin.

**Frontend upload flow (multi-step wizard):**
1. User selects a product, then uploads a CSV file
2. Site parses headers and shows a **column mapping UI** — each CSV header gets a
   dropdown to select which site field it maps to
3. **Auto-detect common aliases** so most CSVs work without manual mapping:
   - `Mfr` / `MFG` / `Manufacturer` → `manufacturer`
   - `P/N` / `Part Number` / `MPN` → `part_number`
   - `Ref Des` / `RefDes` / `Designator` / `Reference` → `reference_designator`
   - `Qty` / `Quantity` / `Count` → `quantity`
   - `Type` / `Component Type` → `component_type`
   - `Package` / `Footprint` / `Package Type` → `package_type`
   - `Value` / `Nominal Value` → `primary_value`
   - `Description` / `Desc` → `description`
   - `Location` / `Board Location` → `location_description`
   - `Notes` / `Comments` → `notes`
4. User corrects any unmatched columns, previews parsed rows in a table
5. Submit — backend creates/links components in bulk

**Admin side:**
- Use `django-import-export` library — provides import button in admin with column
  mapping, preview, and dry-run mode out of the box. Much less custom code needed.
- Add to both `ComponentAdmin` and `ProductComponentAdmin`

**Key design decisions:**
- **Component matching:** lookup-or-create by `(manufacturer, part_number)`. If a
  component already exists, reuse it; otherwise create a new one.
- **Product context:** BOM import is always in the context of a specific product
  (launched from product detail page, or product selected first in a wizard).
- **Row-level validation:** Bad rows should not kill the whole import. Show per-row
  errors and let users fix or skip individual rows.
- **Dry-run preview:** Show what will be created vs. matched before committing.
- **Backend endpoint:** `POST /api/products/{id}/import_bom/` accepting multipart
  form data (CSV file + column mapping JSON).

**Estimated effort:** 3-5 days (backend endpoint + admin import + frontend wizard UI)

#### Week 12-13: Polish & UX Improvements
- ✅ Mobile responsive design (tabs, tables, forms, search)
- ✅ Progressive Web App (PWA) capabilities
- ✅ Image optimization and lazy loading (LazyImage component)
- ✅ Search performance optimization — PostgreSQL full-text search (SearchVector/SearchRank with GIN indexes), pg_trgm trigram indexes on 8 text fields, N+1 cross-reference fix (Feb 13, 2026)
- ✅ User onboarding flow (OnboardingTips component with dismissable tips)
- ✅ Tutorial/help system (Keyboard shortcuts modal, ? to open)

#### Week 14: Testing & Documentation ✅ COMPLETE
- ✅ Unit tests for critical paths (pytest + vitest)
- ✅ Integration tests (backend workflow tests)
- ✅ API documentation (Swagger/OpenAPI via drf-spectacular)
- ⬜ User documentation
- ✅ Deployment documentation (junkbin-deploy.sh, update.sh, backup.sh, restore.sh)
- ✅ Security audit (Feb 3, 2026 — see `Docs/SECURITY_AUDIT.md`)

##### Test Coverage Implemented:
**Backend (pytest + factory_boy):**
- Users: Reputation system, trusted user promotion, permissions
- Reports: 3-strike system, report resolution, user reviews
- Submissions: Approval/rejection workflow, status transitions
- Products: Slug generation, component counts, view counts
- Components: Usage count tracking
- Integration: Full submission workflow, reputation flow

**Frontend (vitest + MSW + testing-library):**
- AuthContext: Login, logout, token restoration
- API Client: Token refresh, authorization headers, retry logic
- Login/Register pages: Form validation, error handling
- AddComponentForm: Search mode, new mode, submission
- ImageUpload: File validation, drag/drop, upload
- Submit wizard: Step progression, form validation

### Phase 3: Advanced Features (Weeks 15-20)

#### Community Features
- ✅ User comments on products
- ⬜ Component verification voting
- ⬜ User-to-user messaging
- ✅ Contribution leaderboards
- ⬜ Community guidelines enforcement

#### Integration & Automation
- ⬜ Octopart API integration (component cross-reference)
- ⬜ DigiKey/Mouser API (availability/pricing)
- ⬜ Datasheet auto-linking
- ⬜ AI-assisted component recognition from images
- ⬜ iFixit integration for repair guides
- ⬜ Discord/Slack webhooks for notifications

#### Infrastructure & Operations
- ✅ Admin system status dashboard — PostgreSQL, Redis, Celery workers, Celery Beat health checks; CPU/memory/disk metrics; recent task history; app stats; quick links (Feb 12, 2026)
- ✅ Nginx cache headers — `no-cache` on index.html, immutable caching on hashed assets, proper 404 for missing assets (Feb 12, 2026)
- ✅ Docker healthcheck fix — IPv4 `127.0.0.1` instead of `localhost` (IPv6 resolution issue) (Feb 12, 2026)

#### Advanced Analytics
- ⬜ Prometheus metrics
- ⬜ Grafana dashboards
- ⬜ Component popularity tracking
- ⬜ Search analytics
- ⬜ User engagement metrics

---

## Deployment Script Features

The `junkbin-deploy.sh` script will handle:

### Pre-flight Checks
- Detect Linux distribution (Ubuntu/Debian/Fedora/Arch)
- Check system requirements (RAM, disk space)
- Verify user has sudo privileges
- Check for port conflicts (80, 443, 5432, 6379)

### Dependency Installation
- Docker & Docker Compose
- Git
- SSL certificate tools (certbot)
- System utilities (curl, wget, etc.)

### Security Hardening
- Configure firewall (ufw/firewalld)
- Install and configure fail2ban
- SSH hardening (disable root login, key-only auth)
- Set up automatic security updates

### Application Deployment
- Clone repository
- Create `.env` file from template
- Generate secure random keys
- Initialize database
- Run migrations
- Create superuser account
- Collect static files
- Start Docker containers

### SSL/TLS Setup
- Domain verification
- Let's Encrypt certificate generation
- Auto-renewal cron job
- HTTPS redirect configuration

### Backup Configuration ✅ COMPLETE
- ~~Daily PostgreSQL dumps~~ — `deployment/backup.sh` (Docker + `--dev` mode)
- ~~Image file backups~~ — media backed up from Docker volume
- ~~Retention policy (30 days)~~ — auto-cleanup of old backups
- ~~Backup restoration testing~~ — `deployment/restore.sh` with interactive menu, selective restore (Feb 11, 2026)

### Monitoring Setup
- ✅ Health check endpoints (`/api/health/`, nginx `/health`)
- ✅ Admin system status dashboard (`/admin/system-status/`) — service health, system metrics, Celery task history, app stats, quick links (Feb 12, 2026)
- Log rotation (logrotate)
- Disk space monitoring
- Service restart on failure (systemd)

### Update & Maintenance
- Pull latest code
- Apply migrations
- Restart services
- Zero-downtime deployment (future)

---

## Cyberpunk Aesthetic Elements

### Color Palette (Implemented)
- **cyber-black**: #0a0a0f (deep black)
- **cyber-darker**: #0d0d14 (darker bg)
- **cyber-dark**: #12121a (dark bg)
- **cyber-gray**: #1a1a24 (card bg)
- **cyber-light**: #2a2a3a (borders)
- **cyber-cyan**: #05d9e8 (primary - products)
- **cyber-pink**: #ff2a6d (secondary - components)
- **cyber-green**: #39ff14 (tertiary - schematics)
- **cyber-yellow**: #f9f002 (warning/featured)

### Typography
- **Headers**: Orbitron, Rajdhani, or Share Tech Mono
- **Body**: Inter or Roboto
- **Code/Technical**: Fira Code or JetBrains Mono

### Visual Effects (Implemented)
- ✅ Scanlines overlay effect (.scanlines)
- ✅ Glitch text animation (.glitch with data-text)
- ✅ Neon glow on buttons and cards
- ✅ Grid background pattern
- ✅ Chromatic aberration on hover (.chromatic-aberration)
- ✅ CRT flicker effect (.crt)
- ✅ Terminal-styled inputs with glow (.terminal-input)
- ✅ Blinking cursor animation (.blink)
- ✅ Neon pulsing border (.neon-border)
- ✅ Static noise overlay (.noise)

### "NO USER SERVICEABLE PARTS INSIDE" Placement
1. **Background watermark** - Ghosted on main pages
2. **Login page** - Diagonal across background
3. **404 page** - Featured prominently with glitch effect
4. **Favicon** - Stylized "NUSPI" or warning symbol
5. **Page source comments** - ASCII art version
6. **Footer** - Small text with strikethrough
7. **About page** - Ironic mission statement
8. **Loading screens** - Animated text
9. **Error messages** - "WARNING: NO USER SERVICEABLE PARTS INSIDE... just kidding, tear it apart!"
10. **Easter egg** - Konami code reveals full manifesto

---

## API Endpoints (RESTful)

### Authentication
- `POST /api/auth/register` - User registration
- `POST /api/auth/login` - User login
- `POST /api/auth/logout` - User logout
- `POST /api/auth/verify-email` - Email verification
- `POST /api/auth/reset-password` - Password reset
- `GET /api/auth/oauth/google` - Google OAuth

### Products
- `GET /api/products` - List products (paginated, filterable)
- `POST /api/products` - Create product
- `GET /api/products/{id}` - Get product details
- `PUT /api/products/{id}` - Update product
- `DELETE /api/products/{id}` - Delete product (admin only)
- `GET /api/products/{id}/components` - Get product's component list
- `POST /api/products/{id}/images` - Upload product images

### Components
- `GET /api/components` - Search components
- `POST /api/components` - Create component
- `GET /api/components/{id}` - Get component details
- `PUT /api/components/{id}` - Update component
- `GET /api/components/{id}/products` - Products containing this component

### Submissions
- `GET /api/submissions` - List pending submissions (admin)
- `POST /api/submissions` - Submit new product/update
- `PUT /api/submissions/{id}/approve` - Approve submission (admin)
- `PUT /api/submissions/{id}/reject` - Reject submission (admin)

### Reports
- `POST /api/reports` - Submit report
- `GET /api/reports` - List reports (admin)
- `PUT /api/reports/{id}/resolve` - Resolve report (admin)

### User
- `GET /api/users/{id}` - Get user profile
- `GET /api/users/{id}/contributions` - User's contributions
- `GET /api/users/{id}/stats` - User statistics

### Search
- `GET /api/search/products?q={query}` - Search products
- `GET /api/search/components?q={query}` - Search components
- `GET /api/search/cross-reference?part={number}` - Find products with component

---

## Security Considerations

### Authentication
- bcrypt password hashing
- JWT tokens with short expiration
- Refresh token rotation
- Rate limiting on auth endpoints
- CAPTCHA on registration (optional)

### Authorization
- Role-based access control (User, Moderator, Admin)
- Object-level permissions
- API key rate limiting
- CORS configuration

### Data Protection
- SQL injection prevention (ORM)
- XSS protection (input sanitization)
- CSRF tokens
- Secure file uploads (type/size validation)
- Image sanitization (strip EXIF data)

### Infrastructure
- HTTPS only (HSTS headers)
- Security headers (CSP, X-Frame-Options)
- Regular dependency updates
- Automated security scanning
- Log monitoring for suspicious activity

---

## Performance Optimization

### Database
- ✅ Proper indexing on search fields — GIN trigram indexes (pg_trgm) on 8 text fields, GIN indexes on SearchVectorFields
- ✅ Query optimization with select_related/prefetch_related — N+1 fix in cross_reference endpoint
- ✅ Full-text search with relevance ranking — PostgreSQL SearchVector/SearchQuery/SearchRank with weighted fields
- Database connection pooling
- Read replicas for scaling (future)

### Caching
- Redis for session data
- Query result caching
- Static file CDN (future)
- Browser caching headers

### Frontend
- Code splitting
- Lazy loading images
- Service worker for offline support
- Optimized image formats (WebP)
- Minification and compression

---

## Testing Strategy

### Unit Tests ✅ IMPLEMENTED
- Model validation (User, Product, Component, Submission, Report)
- API endpoint responses (via MSW mocks)
- Authentication flows (AuthContext, token refresh)
- Permission checks (IsOwnerOrReadOnly, IsModerator, IsTrustedUser)

**Backend Tools:** pytest, pytest-django, factory_boy
**Frontend Tools:** vitest, @testing-library/react, msw

### Integration Tests ✅ IMPLEMENTED
- User registration to submission workflow
- Submission approval → reputation gain flow
- 3-strike system → user review trigger
- Component linking → count updates
- Report and moderation workflow

### End-to-End Tests ✅ COMPLETE (Feb 10, 2026)
- ✅ 26 API tests against live production (auth, CRUD, uploads, search, reports, newsletter)
- ✅ 10 manual browser tests (mobile, uploads, 404, admin, detail pages, loading, keyboard shortcuts)
- ✅ 5 bugs found and fixed during browser testing
- ✅ Cross-browser compatibility (Chrome only so far)
- ✅ Production data deployed: ~93 components, ~101 Flipper Zero cross-references with reference designators (Feb 11, 2026)

### Running Tests
```bash
# Backend
cd backend
DJANGO_SETTINGS_MODULE=config.settings.test pytest -v
pytest --cov=apps --cov-report=html  # Coverage report

# Frontend
cd frontend
npm run test           # Run all tests
npm run test:coverage  # Coverage report
```

---

## Success Metrics

### Community Growth
- New user registrations per month
- Active contributors (>1 submission/month)
- Total products documented
- Total components cataloged
- Geographic distribution

### Engagement
- Average submissions per user
- Search queries per day
- Component cross-references performed
- Time on site
- Return visitor rate

### Quality
- Report-to-submission ratio
- Average time to review
- User reputation distribution
- Datasheet link completion rate

---

## Future Expansion Ideas

### Technical
- Mobile apps (iOS/Android)
- Browser extension for inline shopping
- API marketplace
- Machine learning for component recognition
- Blockchain verification (component authenticity)
- 3D PCB visualization

### Community
- Regional chapters/meetups
- Certification program for contributors
- Bounty system for hard-to-find teardowns
- Educational content (repair tutorials)
- Sustainability impact tracking

### Business
- Premium features (API access, advanced analytics)
- Partnerships with repair shops
- Component marketplace integration
- Repair service directory
- Corporate sponsorships from manufacturers

---

## License & Legal

### Code License
- MIT or Apache 2.0 (open source)

### Content License
- Creative Commons BY-SA 4.0 for user contributions
- Requires attribution
- Allows commercial use
- Share-alike provision

### Terms of Service
- User-generated content ownership
- Right to remove inappropriate content
- No warranty on data accuracy
- DMCA compliance
- GDPR compliance (right to deletion)

---

## Contributing Guidelines

### Code Contributions
- Fork and pull request workflow
- Code style guide (PEP 8 for Python, ESLint for JS)
- Required tests for new features
- Documentation updates

### Content Contributions
- Photography guidelines (resolution, lighting, angles)
- BOM formatting standards
- Component naming conventions
- Citation of sources

---

## Project Timeline Summary

| Phase | Duration | Key Deliverables |
|-------|----------|------------------|
| Phase 1: MVP | 6 weeks | Core functionality, basic UI, deployment script |
| Phase 2: Enhanced | 8 weeks | Advanced search, moderation, imports, polish |
| Phase 3: Advanced | 6 weeks | Integrations, analytics, community features |
| **Total** | **20 weeks** | **Fully-featured platform** |

---

## Next Steps

1. ~~**Add schematic upload form**~~ ✅ - Schematic upload added to Product detail schematics tab
2. ~~**Test infrastructure**~~ ✅ - Backend (pytest) and frontend (vitest) testing complete
3. ~~**Implement global search**~~ ✅ - Global search page with tabbed results
4. ~~**Add pagination**~~ ✅ - Products, components, and schematics list pages
5. ~~**Run tests and fix issues**~~ ✅ - All tests passing
6. ~~**Mobile responsive polish**~~ ✅ - Tested via Chrome DevTools mobile emulation (Feb 10)
7. **User documentation** - Create user guide for contributors
8. ~~**Security audit**~~ ✅ - Completed Feb 3 (see `Docs/SECURITY_AUDIT.md`)
9. ~~**Production deployment**~~ ✅ - Live at https://junkbin.io with TLS 1.3, HSTS, auto-renewal

---

*"They said 'NO USER SERVICEABLE PARTS INSIDE'... We took that personally."*

**Last Updated**: February 13, 2026
**Version**: 1.8
**Status**: MVP Complete - Phase 2 Complete - Phase 3 In Progress - Deployed & E2E Tested
