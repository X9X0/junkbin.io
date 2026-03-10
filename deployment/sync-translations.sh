#!/bin/bash

################################################################################
# Junkbin.io - Translation Sync Script
#
# Runs MyMemory autotranslate for one language via Weblate, pulls the result
# into the locale file, and commits to git.
#
# MyMemory limit: ~1,000 strings/day with email (~50,000 chars/day).
# Run one language per day. Quota resets midnight UTC (8 PM EST).
#
# Untranslated strings are left empty ("") — i18next returnEmptyString:false
# falls back to English automatically. No English standins needed.
#
# Usage:
#   ./deployment/sync-translations.sh <lang> [--dry-run]
#
#   <lang>      Two-letter language code (e.g. pl, ru, tr)
#   --dry-run   Translate and show results but do not commit to git
#
# Check translation-status.json for per-language progress.
################################################################################

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info()  { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn()  { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }
log_step()  { echo -e "${BLUE}[STEP]${NC} $1"; }

VALID_LANGS="pl pt sk sr sl ru uk ro tr fr es de it nl cs hr hu"
LANG=""
DRY_RUN=false

for arg in "$@"; do
    case $arg in
        --dry-run) DRY_RUN=true ;;
        --*)
            log_error "Unknown option: $arg"
            exit 1
            ;;
        *)
            if echo "$VALID_LANGS" | grep -qw "$arg"; then
                LANG="$arg"
            else
                log_error "Unknown language: $arg"
                log_error "Valid languages: $VALID_LANGS"
                exit 1
            fi
            ;;
    esac
done

if [ -z "$LANG" ]; then
    log_error "Usage: $0 <lang> [--dry-run]"
    log_error "  Example: $0 pl"
    log_error "  Valid languages: $VALID_LANGS"
    log_error "  See deployment/translation-status.json for progress."
    exit 1
fi

WEBLATE_TOKEN="wlu_WXvfM2cqJjFsNkL4NRBe1oQGKBjP0Rha4Sgg"
WEBLATE_BASE="https://translate.junkbin.io/api"
COMPONENT="junkbin-io/frontend-ui"
LOCALES_DIR="frontend/public/locales"
STATUS_FILE="deployment/translation-status.json"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$(dirname "$SCRIPT_DIR")"

log_info "Language: $LANG"

# 1. Check and unlock Weblate component
log_step "Checking Weblate component lock status..."
LOCKED=$(curl -s -H "Authorization: Token $WEBLATE_TOKEN" \
    "$WEBLATE_BASE/components/$COMPONENT/" | python3 -c "import sys,json; print(json.load(sys.stdin).get('locked', False))")

if [ "$LOCKED" = "True" ]; then
    log_warn "Component is locked — unlocking..."
    curl -s -X POST -H "Authorization: Token $WEBLATE_TOKEN" \
        "$WEBLATE_BASE/components/$COMPONENT/lock/" -d "lock=false" > /dev/null
    log_info "Unlocked."
else
    log_info "Component is unlocked."
fi

# 2. Run autotranslate
# filter_type "todo" = untranslated/empty strings only. "all" is not valid in
# Weblate 5.10.4 and silently returns 0. Pending language files are empty so
# "todo" correctly targets all 1044 strings.
log_step "Running MyMemory autotranslate for $LANG..."
RESULT=$(curl -s -X POST \
    -H "Authorization: Token $WEBLATE_TOKEN" \
    -H "Content-Type: application/json" \
    -d '{"mode":"translate","filter_type":"todo","auto_source":"mt","engines":["mymemory"],"threshold":80}' \
    "$WEBLATE_BASE/translations/$COMPONENT/$LANG/autotranslate/")

COUNT=0
if echo "$RESULT" | python3 -c "import sys,json; d=json.load(sys.stdin); exit(0 if 'details' in d else 1)" 2>/dev/null; then
    COUNT=$(echo "$RESULT" | python3 -c "import sys,json,re; d=json.load(sys.stdin); m=re.search(r'(\d+) string', d['details']); print(m.group(1) if m else 0)")
    log_info "$LANG: $COUNT strings updated"
else
    ERROR=$(echo "$RESULT" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('errors',[{}])[0].get('detail','unknown error'))" 2>/dev/null || echo "unknown error")
    log_error "$LANG: $ERROR"
    exit 1
fi

# 3. Pull translated file from Weblate API
# Untranslated strings come back as "" — i18next falls back to English for these.
# Do NOT fill with English standins; empty strings are correct and intentional.
log_step "Pulling translated file from Weblate..."
python3 << PYEOF
import urllib.request, json, sys

TOKEN = "$WEBLATE_TOKEN"
BASE = "$WEBLATE_BASE"
LANG = "$LANG"
LOCALES_DIR = "$LOCALES_DIR"

url = f"{BASE}/translations/junkbin-io/frontend-ui/{LANG}/file/"
req = urllib.request.Request(url, headers={"Authorization": f"Token {TOKEN}"})
try:
    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read().decode())
        path = f"{LOCALES_DIR}/{LANG}/translation.json"
        with open(path, 'w') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        # Count translated (non-empty) strings at the leaf level
        def count_leaves(obj):
            total, translated = 0, 0
            for v in obj.values():
                if isinstance(v, dict):
                    t, tr = count_leaves(v)
                    total += t; translated += tr
                else:
                    total += 1
                    if v and v.strip():
                        translated += 1
            return total, translated
        total, translated = count_leaves(data)
        print(f"  saved: {translated}/{total} strings translated")
except Exception as e:
    print(f"  ERROR — {e}", file=sys.stderr)
    sys.exit(1)
PYEOF

# 4. Update translation-status.json
log_step "Updating translation status..."
python3 << PYEOF
import json, os
from datetime import date

STATUS_FILE = "$STATUS_FILE"
LANG = "$LANG"
COUNT = int("$COUNT")

VALID_LANGS = "$VALID_LANGS".split()

# Load or initialise status file
if os.path.exists(STATUS_FILE):
    with open(STATUS_FILE) as f:
        status = json.load(f)
else:
    status = {}

# Ensure all languages have an entry
for lang in VALID_LANGS:
    if lang not in status:
        status[lang] = {"status": "pending", "last_run": None, "strings_updated": 0}

# Count translated strings in the pulled file
LOCALES_DIR = "$LOCALES_DIR"
with open(f"{LOCALES_DIR}/{LANG}/translation.json") as f:
    data = json.load(f)

def count_leaves(obj):
    total, translated = 0, 0
    for v in obj.values():
        if isinstance(v, dict):
            t, tr = count_leaves(v)
            total += t; translated += tr
        else:
            total += 1
            if v and v.strip():
                translated += 1
    return total, translated

total, translated = count_leaves(data)
pct = round(translated / total * 100) if total else 0

status[LANG] = {
    "status": "complete" if pct >= 95 else "partial",
    "last_run": str(date.today()),
    "strings_updated": COUNT,
    "strings_translated": translated,
    "strings_total": total,
    "percent": pct,
}

with open(STATUS_FILE, 'w') as f:
    json.dump(status, f, indent=2, sort_keys=True)

print(f"  {LANG}: {translated}/{total} ({pct}%) — marked as {status[LANG]['status']}")

# Print summary table
pending = [l for l, v in status.items() if v['status'] == 'pending']
partial = [l for l, v in status.items() if v['status'] == 'partial']
complete = [l for l, v in status.items() if v['status'] == 'complete']
print(f"\n  Complete ({len(complete)}): {' '.join(complete) or 'none'}")
print(f"  Partial  ({len(partial)}):  {' '.join(partial) or 'none'}")
print(f"  Pending  ({len(pending)}): {' '.join(pending) or 'none'}")
PYEOF

if [ "$DRY_RUN" = true ]; then
    log_warn "Dry run — skipping git commit."
    log_info "Done. Review changes with: git diff frontend/public/locales/$LANG/"
    exit 0
fi

# 5. Commit and push
log_step "Committing to git..."
git add "frontend/public/locales/$LANG/translation.json" "$STATUS_FILE"
if git diff --cached --quiet; then
    log_warn "No changes to commit — already up to date."
else
    git commit -m "Sync translations: $LANG ($COUNT strings updated)

$(date -u '+%Y-%m-%d %H:%M UTC') — automated sync via sync-translations.sh

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
    git push
    log_info "Pushed to main."
fi

# 6. Reset Weblate to our HEAD so it stays in sync
# Safe here because translations were already pulled and committed above.
log_step "Syncing Weblate to HEAD..."
curl -s -X POST \
    -H "Authorization: Token $WEBLATE_TOKEN" \
    -H "Content-Type: application/json" \
    -d '{"operation": "reset"}' \
    "$WEBLATE_BASE/components/$COMPONENT/repository/" > /dev/null
log_info "Weblate synced."

echo ""
log_info "Done. Check deployment/translation-status.json for overall progress."
log_info "When all languages are complete, test on [dev]: ./deployment/update.sh --dev"
