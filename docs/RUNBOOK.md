# Junkbin.io — Operations Runbook

> **Purpose:** This document exists so that someone who did not build this site can keep it running. If you're reading this because the original maintainer is unavailable, start at [Succession Handover](#succession-handover).

---

## Table of Contents

1. [Stack Overview](#stack-overview)
2. [Succession Handover](#succession-handover)
3. [Secrets & Credentials Inventory](#secrets--credentials-inventory)
4. [Day-to-Day Operations](#day-to-day-operations)
5. [Updating the Application](#updating-the-application)
6. [Backup & Restore](#backup--restore)
7. [Fresh Server Deployment](#fresh-server-deployment)
8. [SSL Certificate Management](#ssl-certificate-management)
9. [Monitoring & Alerting](#monitoring--alerting)
10. [Troubleshooting](#troubleshooting)
11. [Architecture Reference](#architecture-reference)

---

## Stack Overview

Junkbin.io is a Django + React application running entirely in Docker Compose.

| Container | Image | Role |
|---|---|---|
| `junkbin_postgres` | postgres:15-alpine | PostgreSQL database |
| `junkbin_redis` | redis:7-alpine | Cache + Celery broker |
| `junkbin_backend` | junkbinio-backend (local build) | Django/Gunicorn API |
| `junkbin_celery` | junkbinio-backend | Background task worker |
| `junkbin_celery_beat` | junkbinio-backend | Scheduled task scheduler |
| `junkbin_frontend` | junkbinio-frontend (local build) | React/Vite build (build-only, exits) |
| `junkbin_nginx` | nginx:alpine | Reverse proxy + SSL termination |
| `junkbin_prometheus` | prom/prometheus | Metrics collection |
| `junkbin_grafana` | grafana/grafana | Monitoring dashboards |

**Key Docker volumes** (data lives here, not in the repo):
- `junkbinio_postgres_data` — all database data
- `junkbinio_media_files` — uploaded images, PDFs, schematics
- `junkbinio_frontend_build` — compiled React assets (ephemeral, rebuilt on deploy)

**Project root:** `/root/junkbin.io` on the production server. Verify with `docker inspect junkbin_nginx --format "{{range .Mounts}}{{.Source}}{{\"\\n\"}}{{end}}"` rather than assuming — this document previously named the maintainer's *dev* path here, which sent a 2026-09-09 incident response `cd`-ing into a nonexistent directory.

---

## Succession Handover

If you are taking over maintainership, work through this checklist in order.

### Step 1 — Get access

You need all of these before you can operate the site:

- [ ] **SSH access** to the production server (ask for your public key to be added, or get the existing private key from the secrets vault)
- [ ] **GitHub repository access** — request to be added as a collaborator, or transfer the repo to an org you control
- [ ] **Domain registrar access** — to renew the domain and update DNS if needed
- [ ] **Secrets vault access** — see [Secrets & Credentials Inventory](#secrets--credentials-inventory)
- [ ] **Hosting provider access** — to manage the VPS (restart, resize, rebuild if the server dies)

### Step 2 — Verify the site is working

```bash
# SSH into the server
ssh user@<server-ip>

# Check all containers are running
cd /root/junkbin.io
docker compose -f docker-compose.yml ps

# All of these should show "running" or "Up":
# junkbin_postgres, junkbin_redis, junkbin_backend,
# junkbin_celery, junkbin_celery_beat, junkbin_nginx

# Quick health check
curl -s http://localhost/api/health/ | python3 -m json.tool
```

### Step 3 — Verify off-host backups are running

A separate machine pulls backups twice daily. Check the log to confirm transfers are still succeeding:

```bash
tail -5 Docs/Prod_Backups/transfer.log
```

Each line should show `SUCCESS`. If the log hasn't updated in over 24 hours, the pull job on the backup machine needs attention.

### Step 4 — Confirm you can deploy an update

```bash
cd /root/junkbin.io
./deployment/update.sh --skip-pull   # dry run with existing code
```

If that works without errors, you can deploy updates.

### Step 5 — Transfer ongoing costs

- Domain renewal (check registrar — note the expiry date)
- VPS/hosting monthly bill
- Email provider (if not using free tier)

---

## Secrets & Credentials Inventory

All secrets live in `/root/junkbin.io/.env` on the server. **This file is not in version control.**

### What's in .env

| Variable | What it is | Where to get a new one |
|---|---|---|
| `SECRET_KEY` | Django cryptographic key — changing this invalidates all sessions | `openssl rand -base64 64` |
| `POSTGRES_PASSWORD` | Database password | Generate new, update DATABASE_URL to match |
| `DATABASE_URL` | Full DB connection string | Constructed from POSTGRES_* vars |
| `EMAIL_HOST_PASSWORD` | SMTP password or app-specific password | Your email provider |
| `OAUTH_GOOGLE_CLIENT_ID` / `_SECRET` | Google OAuth for login | Google Cloud Console |
| `NEXAR_CLIENT_ID` / `_SECRET` | Octopart component data API | nexar.com |
| `GRAFANA_ADMIN_PASSWORD` | Monitoring dashboard login | Set to whatever you want |

### Backup the .env file

```bash
# Copy .env to a secure location off-server (e.g., password manager, encrypted drive)
cat /root/junkbin.io/.env
```

The `deployment/backup.sh` script automatically includes `.env.backup` in each backup archive. Treat backup archives as sensitive — they contain credentials.

### SSL certificates

Managed by Let's Encrypt / Certbot via the DNS-01 challenge (`certbot-dns-hostinger`, installed in the `/opt/certbot` venv). Certificates live at `/etc/letsencrypt/live/junkbin.io/`. They auto-renew via a cron job, with a daily expiry monitor as backstop. See [SSL Certificate Management](#ssl-certificate-management).

---

## Day-to-Day Operations

All commands run from the project root. Production uses the explicit `-f docker-compose.yml` flag to avoid merging the dev override file.

### Check status

```bash
cd /root/junkbin.io
docker compose -f docker-compose.yml ps
```

### View logs

```bash
# All services, follow
docker compose -f docker-compose.yml logs -f

# Single service
docker compose -f docker-compose.yml logs -f backend
docker compose -f docker-compose.yml logs -f nginx
docker compose -f docker-compose.yml logs -f celery
```

### Restart a service

```bash
docker compose -f docker-compose.yml restart backend
docker compose -f docker-compose.yml restart nginx
```

### Restart everything

```bash
docker compose -f docker-compose.yml down
docker compose -f docker-compose.yml up -d
```

### Run Django management commands

```bash
# General form
docker compose -f docker-compose.yml exec backend python manage.py <command>

# Examples
docker compose -f docker-compose.yml exec backend python manage.py shell
docker compose -f docker-compose.yml exec backend python manage.py migrate
docker compose -f docker-compose.yml exec backend python manage.py createsuperuser

# Reset a locked-out admin account (django-axes lockout)
docker compose -f docker-compose.yml exec backend python manage.py axes_reset
```

### Access the database directly

```bash
docker exec -it junkbin_postgres psql -U junkbin junkbin
```

### Monitor disk space

```bash
df -h
docker system df   # shows how much Docker is using
```

---

## Updating the Application

Use the `update.sh` script — it handles git pull, image rebuild, volume cleanup, migrations, and static files in the correct order.

```bash
cd /root/junkbin.io
./deployment/update.sh
```

**What it does:**
1. `git pull` — fetches latest code
2. Rebuilds backend and frontend Docker images
3. Removes the stale `frontend_build` volume (necessary — old JS bundles otherwise persist)
4. Brings all containers back up
5. Runs `migrate` and `collectstatic`

**Options:**
```bash
./deployment/update.sh --skip-pull   # if you already pulled manually
./deployment/update.sh --seed        # also runs seed_data after migrate
```

**After an update:** Users may see an old cached version due to the PWA service worker. They need `Ctrl+Shift+R` or to unregister the service worker in DevTools → Application → Service Workers. This is normal behaviour — nothing is broken.

### Rebuilding only the frontend

If you changed only frontend code and want a faster rebuild:

```bash
docker compose -f docker-compose.yml build --no-cache frontend
docker compose -f docker-compose.yml rm -sf frontend nginx
docker volume rm junkbinio_frontend_build
docker compose -f docker-compose.yml up -d frontend nginx
```

---

## Backup & Restore

### Taking a backup

```bash
cd /root/junkbin.io
./deployment/backup.sh
```

Backups are saved to `./backups/` as `junkbin_backup_YYYYMMDD_HHMMSS.tar.gz`. Each archive contains:
- `database.sql` — full PostgreSQL dump
- `media.tar.gz` — all uploaded files (images, PDFs, schematics)
- `.env.backup` — environment/secrets snapshot
- `manifest.txt` — metadata

Backups older than 30 days are automatically pruned.

### Automated backups

A root cron entry runs `deployment/backup.sh` at 02:00 and 14:00, writing to
`./backups/` (where the off-host puller looks, ~15 minutes later each time) and
logging to `/var/log/junkbin-backup.log`:

```bash
sudo crontab -l | grep backup.sh
sudo tail -30 /var/log/junkbin-backup.log
```

> **If you see `/opt/junkbin-backups/backup.sh` in the crontab, it is the old
> broken job — replace it.** That script `cd`'d to a hardcoded `/opt/junkbin.io`,
> piped `pg_dump` into `gzip` without `pipefail` (so a failed dump still produced
> a valid, empty `.gz` that looked like a successful backup), and pruned
> `*.gz` older than 30 days — which would delete genuine backups while leaving
> the empty ones. It also archived `./backend/media`, but media lives in the
> `media_files` Docker volume at `/app/media`. Re-running
> `sudo ./deployment/junkbin-deploy.sh` replaces the entry.

### Verifying a backup is real

Size alone is the tell — an empty dump still compresses to a valid archive:

```bash
ls -lh backups/ | tail -5              # a real archive is MBs, not bytes
tar -tzf backups/junkbin_backup_*.tar.gz | head   # should list database.sql, media.tar.gz, manifest.txt
```

### Off-host backups (automated)

A separate machine pulls backups from the production server twice daily at approximately **02:15** and **14:15**. The pulled archives and a transfer log are stored at:

```
Docs/Prod_Backups/
├── junkbin_backup_YYYYMMDD_HHMMSS.tar.gz   (one per run)
└── transfer.log                             (download history)
```

**Verifying backups are healthy:**
```bash
tail -10 Docs/Prod_Backups/transfer.log
# Every line should end with SUCCESS
# The most recent entry should be from today (or yesterday at worst)
```

If you see `SKIP` entries, that means the archive already existed locally — not an error. If you see failures or the log stops updating, the pull job on the backup machine has stopped and needs investigation.

### Restoring from backup

The restore script is interactive — it shows a menu so you can choose what to restore.

```bash
cd /root/junkbin.io
./deployment/restore.sh backups/junkbin_backup_20260228_020000.tar.gz
```

**Menu options:**
- `[1]` Database — restores all products, components, users, listings
- `[2]` Media files — restores uploaded images and PDFs
- `[3]` User accounts — keep backup users vs. wipe and create fresh admin
- `[4]` .env config — restore the backed-up secrets (off by default — be careful)

**Non-interactive restore** (e.g., in a script):
```bash
./deployment/restore.sh --yes backups/junkbin_backup_20260228_020000.tar.gz
```

**After restore:** Verify the site works:
```bash
curl -s https://junkbin.io/api/health/
```

### Verifying a backup (test restore)

Periodically test that backups actually work by restoring to a throwaway server. A backup you've never restored from is a backup you don't have.

---

## Fresh Server Deployment

Use this when standing up the site on a new server from scratch.

### Prerequisites

- Fresh Linux server (Ubuntu 22.04/24.04, Debian, Fedora, Arch, RHEL/CentOS/Alma/Rocky)
- Minimum 2GB RAM, 10GB free disk
- Domain DNS already pointing to the new server's IP
- Root/sudo access

### Steps

```bash
# 1. Clone the repository
git clone https://github.com/YOUR_USERNAME/junkbin.io.git
cd junkbin.io

# 2. Run the deploy script (prompts for domain + email)
sudo ./deployment/junkbin-deploy.sh
```

The script installs Docker, configures the firewall (UFW/firewalld), sets up fail2ban, obtains an SSL certificate from Let's Encrypt, builds and starts all containers, runs migrations, and sets up a daily backup cron job.

### After fresh deploy

1. Configure email in `.env` (`EMAIL_HOST_PASSWORD`)
2. Configure OAuth in `.env` (`OAUTH_GOOGLE_CLIENT_ID`, `OAUTH_GOOGLE_CLIENT_SECRET`)
3. Restart services: `docker compose -f docker-compose.yml up -d`
4. Restore data from backup: `./deployment/restore.sh <backup_file>`
5. Create an admin account: `docker compose -f docker-compose.yml exec backend python manage.py createsuperuser`
6. Verify: visit `https://junkbin.io/admin`

### Restoring data onto a fresh server

```bash
# After junkbin-deploy.sh has run and containers are up:
./deployment/restore.sh backups/junkbin_backup_YYYYMMDD_HHMMSS.tar.gz
```

Choose to restore database + media. Choose "keep current .env" (option 4 off) since the fresh deploy already generated a working `.env` — or restore the backed-up one if it has configured secrets you need.

---

## SSL Certificate Management

Certificates are issued by Let's Encrypt and managed by Certbot.

### Check certificate status

```bash
sudo /opt/certbot/bin/certbot certificates

# Or check what is actually being served (catches "renewed but nginx not reloaded"):
for h in junkbin.io www.junkbin.io translate.junkbin.io; do
  echo "== $h"
  echo | openssl s_client -servername "$h" -connect "$h:443" 2>/dev/null | openssl x509 -noout -dates
done
```

### Manual renewal

> **Always use the absolute venv path `/opt/certbot/bin/certbot`.**
> These certs use the `dns-hostinger` DNS-01 authenticator, and that plugin is
> installed **only** in the `/opt/certbot` venv. A bare `certbot` resolves to the
> distro package, which has no such plugin and will fail. This is exactly how the
> certs expired in Sep 2026 — the renewal cron called bare `certbot` and cron's
> PATH (`/usr/bin:/bin`) excludes the `/usr/local/bin` symlink.

```bash
sudo /opt/certbot/bin/certbot renew
docker compose -f docker-compose.yml exec -T nginx nginx -s reload
```

### Auto-renewal

A root cron entry runs at 03:00 and 15:00 daily:

```bash
sudo crontab -l | grep certbot
```

It calls the venv certbot by absolute path and reloads nginx via
`--deploy-hook`, so the reload fires only on an actual renewal. Output is
appended to `/var/log/junkbin-certbot-renew.log` — check there first when a
renewal is suspect:

```bash
sudo tail -50 /var/log/junkbin-certbot-renew.log
```

Re-running `sudo ./deployment/junkbin-deploy.sh` replaces a stale or broken
renewal cron entry rather than skipping it.

### Expiry monitoring

`deployment/cert-monitor.sh` runs daily via `junkbin-cert-monitor.timer` and
emails `JUNKBIN_ADMIN_EMAIL` when any host is within 21 days of expiry
(critical at 7 days, and when already expired). It inspects the cert **served
over TLS**, not the files on disk, so it also catches "renewed on disk but nginx
was never reloaded".

```bash
systemctl status junkbin-cert-monitor.timer
sudo /root/junkbin.io/deployment/cert-monitor.sh   # run on demand
```

### Certificate location

```
/etc/letsencrypt/live/junkbin.io/fullchain.pem
/etc/letsencrypt/live/junkbin.io/privkey.pem
```

These are bind-mounted into the nginx container via `docker-compose.yml` (`/etc/letsencrypt:/etc/letsencrypt:ro`).

### If the certificate expires and the site is down

First just try a normal renewal — the DNS-01 challenge does not need port 80,
so nginx can keep running:

```bash
sudo /opt/certbot/bin/certbot renew
cd /root/junkbin.io && docker compose -f docker-compose.yml exec -T nginx nginx -s reload
```

Only if the Hostinger DNS credentials are the problem (check
`/etc/letsencrypt/hostinger.ini` and the renewal log) fall back to standalone,
which needs port 80 free:

```bash
# Stop nginx so certbot can bind port 80
docker compose -f docker-compose.yml stop nginx

sudo /opt/certbot/bin/certbot certonly --standalone -d junkbin.io -d www.junkbin.io
sudo /opt/certbot/bin/certbot certonly --standalone -d translate.junkbin.io

# Start nginx again
docker compose -f docker-compose.yml start nginx
```

Note `translate.junkbin.io` is a **separate certificate lineage** — renewing the
apex does not renew it. Check both.

---

## Monitoring & Alerting

Two systemd timers watch for the failures most likely to take the site down
quietly. Both are silent when healthy — **no news is good news**, which also
means a broken monitor is indistinguishable from a healthy system unless you
check it. See [Verifying alerts still work](#verifying-alerts-still-work).

| Timer | Runs | Watches | Warns at | Critical at |
|---|---|---|---|---|
| `junkbin-cert-monitor.timer` | daily | TLS cert expiry, all 3 hostnames | 21 days | 7 days, or expired |
| `junkbin-disk-monitor.timer` | hourly | root filesystem usage | 80% | 90% |

```bash
systemctl list-timers 'junkbin*' --all
journalctl -t junkbin-cert-monitor --since '7 days ago'
journalctl -t junkbin-disk-monitor --since '7 days ago'
```

### Why these exist

The certificates expired on 2026-09-09 because the renewal cron had been failing
for roughly a month and nothing was watching. The renewal bug is fixed, but the
deeper problem was the absence of a second pair of eyes — so the cert monitor
checks the certificate **served over TLS**, not the files on disk. That also
catches "renewed successfully but nginx was never reloaded", which happened
during that very incident.

### Where alerts go

Both monitors resolve the recipient from `.env`, first non-empty wins:

| Source | Notes |
|---|---|
| `JUNKBIN_ADMIN_EMAIL` env var | override, for testing only |
| `ALERT_EMAIL` in `.env` | **the one to edit** — comma-separated list allowed |
| `ADMIN_EMAIL` in `.env` | fallback |
| `root` | last resort, effectively means nobody |

`ALERT_EMAIL` is deliberately separate from `ADMIN_EMAIL`, which is also the
certbot registration address and the app's sending identity — changing one
should not silently change the others.

To change who gets paged, edit `ALERT_EMAIL` in `.env`. No restart or reinstall
is needed; the monitors read it on each run. **Do not put addresses in
`/etc/default/junkbin-monitor`** — that file exists only to supply `JUNKBIN_DIR`
so the monitors can find `.env`.

### How alerts are delivered

Through the app's authenticated SMTP relay (`deployment/alert-lib.sh`, shared by
both monitors), *not* `mail(1)`.

This is deliberate and worth preserving: **this host has no `mail` binary, and
exim is installed but not running.** Any monitor that calls `mail -s` here
delivers to nothing, falls back to stderr, and has its output swallowed by the
systemd timer. A local MTA is not the fix either — mail from a cloud IP with no
SPF or DKIM is mostly spam-filtered, which recreates the same silence one layer
down.

Delivery outcome is always logged, including failure:

```bash
journalctl -t junkbin-cert-monitor | grep -E 'delivered|DELIVERY FAILED'
```

A line reading `ALERT DELIVERY FAILED` names the intended recipient, and means
alerts are not reaching anyone — treat it as urgent as the alert itself.

### Verifying alerts still work

Silence is ambiguous, so test delivery periodically — and always after changing
`.env`, SMTP credentials, or the mail provider. Lower a threshold to force an
alert against a perfectly healthy system:

```bash
# Forces a WARNING; nothing is actually wrong
DISK_WARN_PCT=1 DISK_CRIT_PCT=99 /root/junkbin.io/deployment/disk-monitor.sh
CERT_WARN_DAYS=9999 CERT_CRIT_DAYS=0 /root/junkbin.io/deployment/cert-monitor.sh

# Then confirm it actually went out
journalctl -t junkbin-disk-monitor -n 2
journalctl -t junkbin-cert-monitor -n 2
```

Expect `alert delivered via SMTP to <recipients>`. Check the inbox too — a
relay that accepts a message has not proven it escaped a spam filter.

### Installing or reinstalling a monitor

`junkbin-deploy.sh` does this automatically. By hand, or after editing a unit
file (a `git pull` alone does **not** take effect — the unit must be re-copied
and systemd reloaded):

```bash
cd /root/junkbin.io
sed "s|__DEPLOY_DIR__|$PWD|g" deployment/systemd/junkbin-cert-monitor.service \
    > /etc/systemd/system/junkbin-cert-monitor.service
cp deployment/systemd/junkbin-cert-monitor.timer /etc/systemd/system/
systemctl daemon-reload
systemctl enable --now junkbin-cert-monitor.timer
```

The units ship with a `__DEPLOY_DIR__` placeholder rather than a literal path;
substitute it or the service will point at a directory that does not exist.

---

## Troubleshooting

### Site is down — first steps

```bash
# 1. Check container status
docker compose -f docker-compose.yml ps

# 2. Check nginx (the front door)
docker compose -f docker-compose.yml logs --tail=50 nginx

# 3. Check backend
docker compose -f docker-compose.yml logs --tail=50 backend

# 4. Check health endpoint directly (bypasses nginx)
curl http://localhost:8000/api/health/
```

### A container is crash-looping

```bash
docker compose -f docker-compose.yml logs --tail=100 <service>
```

Common causes:
- **backend**: Bad `.env` value, DB not ready yet, migration error
- **postgres**: Disk full, volume permission issue
- **nginx**: SSL cert missing or expired, config syntax error

### Disk is full

```bash
df -h
du -sh /root/junkbin.io/backups/*   # old backups
docker system prune -f                    # remove unused Docker images/layers
```

### Database connection errors

```bash
# Verify postgres is healthy
docker exec junkbin_postgres pg_isready -U junkbin

# Check DATABASE_URL in .env matches POSTGRES_* vars
grep DATABASE_URL /root/junkbin.io/.env
grep POSTGRES_ /root/junkbin.io/.env
```

### Admin login not working / locked out

```bash
# Reset django-axes lockout (brute-force protection)
docker compose -f docker-compose.yml exec backend python manage.py axes_reset

# Reset a specific user's password
docker compose -f docker-compose.yml exec backend python manage.py shell -c "
from django.contrib.auth import get_user_model
User = get_user_model()
u = User.objects.get(username='admin')
u.set_password('newpassword')
u.save()
print('Done')
"
```

### Celery tasks not running

```bash
docker compose -f docker-compose.yml logs --tail=50 celery
docker compose -f docker-compose.yml logs --tail=50 celery-beat

# Restart celery
docker compose -f docker-compose.yml restart celery celery-beat
```

### Media files not showing

Media files live in the `junkbinio_media_files` Docker volume, not on the host filesystem. To inspect:

```bash
docker exec junkbin_backend find /app/media -type f | head -20
```

To copy files into the volume:
```bash
docker cp /local/path/file.jpg junkbin_backend:/app/media/
```

### After changing .env

Environment variables are not picked up by a `restart`. You must recreate the containers:

```bash
docker compose -f docker-compose.yml up -d
```

### Frontend shows stale/old version

Users may be seeing a cached version via the PWA service worker. Instruct them to:
- Press `Ctrl+Shift+R` (hard reload)
- Or: DevTools → Application → Service Workers → Unregister

To force a fresh build yourself:
```bash
docker compose -f docker-compose.yml build --no-cache frontend
docker compose -f docker-compose.yml rm -sf frontend nginx
docker volume rm junkbinio_frontend_build
docker compose -f docker-compose.yml up -d frontend nginx
```

---

## Architecture Reference

### File layout

```
junkbin.io/
├── backend/               # Django project
│   ├── apps/              # Django apps (products, components, users, api, ...)
│   ├── config/            # Settings, URLs, admin, WSGI
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/              # React/Vite project
│   ├── src/
│   ├── Dockerfile         # Multi-stage: node build → alpine dist-only
│   └── package.json       # Version number lives here
├── deployment/
│   ├── backup.sh          # Backup script
│   ├── restore.sh         # Restore script
│   ├── update.sh          # Rolling update script
│   ├── junkbin-deploy.sh  # Fresh server deploy script
│   ├── nginx/             # Nginx configs
│   ├── systemd/           # systemd service files
│   └── logrotate/
├── docker-compose.yml     # Production stack
├── docker-compose.override.yml  # Dev overrides (no SSL)
├── .env                   # Secrets — NOT in git
└── .env.example           # Template — safe to share
```

### Production vs. development

| | Production | Development |
|---|---|---|
| Compose command | `docker compose -f docker-compose.yml` | `docker compose` (auto-merges override) |
| SSL | Yes (Let's Encrypt) | No |
| Nginx config | `junkbin.conf` | `junkbin-local.conf` |
| `DEBUG` | `False` | `True` |
| `SECURE_SSL_REDIRECT` | `True` | `False` |

### Monitoring

- Grafana: `https://junkbin.io/grafana` (login: admin / see `GRAFANA_ADMIN_PASSWORD` in `.env`)
- Prometheus: `https://junkbin.io/prometheus`
- Health endpoint: `https://junkbin.io/api/health/`

### Key management commands

| Command | What it does |
|---|---|
| `manage.py migrate` | Apply DB schema changes |
| `manage.py collectstatic` | Copy static files for nginx |
| `manage.py createsuperuser` | Create admin account |
| `manage.py axes_reset` | Clear login lockouts |
| `manage.py seed_data` | Load sample data (dev/staging only) |
| `manage.py import_flipper_schematics` | Import Flipper Zero schematics |

---

*Last updated: 2026-02-28*
