#!/bin/bash

################################################################################
# Junkbin.io - Translation Sync Script
#
# Runs MyMemory autotranslate for all languages via Weblate, pulls the results
# into locale files, fills any remaining gaps with English fallbacks, and
# commits everything to git.
#
# Run from project root after MyMemory quota resets (midnight UTC / 8 PM EST).
#
# Usage: ./deployment/sync-translations.sh [--dry-run]
#   --dry-run   Run autotranslate and show results but do not commit to git
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

DRY_RUN=false
for arg in "$@"; do
    case $arg in
        --dry-run) DRY_RUN=true ;;
        *) log_error "Unknown option: $arg"; exit 1 ;;
    esac
done

WEBLATE_TOKEN="wlu_WXvfM2cqJjFsNkL4NRBe1oQGKBjP0Rha4Sgg"
WEBLATE_BASE="https://translate.junkbin.io/api"
COMPONENT="junkbin-io/frontend-ui"
LOCALES_DIR="frontend/public/locales"

# All non-English languages — previously failing ones first to get quota priority
LANGS="pl pt sk sr sl ru uk ro tr fr es de it nl cs hr hu"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$(dirname "$SCRIPT_DIR")"

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

# 2. Run autotranslate for all languages
log_step "Running MyMemory autotranslate..."
TOTAL_UPDATED=0
for lang in $LANGS; do
    RESULT=$(curl -s -X POST \
        -H "Authorization: Token $WEBLATE_TOKEN" \
        -H "Content-Type: application/json" \
        -d '{"mode":"translate","filter_type":"todo","auto_source":"mt","engines":["mymemory"],"threshold":80}' \
        "$WEBLATE_BASE/translations/$COMPONENT/$lang/autotranslate/")

    if echo "$RESULT" | python3 -c "import sys,json; d=json.load(sys.stdin); exit(0 if 'details' in d else 1)" 2>/dev/null; then
        COUNT=$(echo "$RESULT" | python3 -c "import sys,json,re; d=json.load(sys.stdin); m=re.search(r'(\d+) string', d['details']); print(m.group(1) if m else 0)")
        echo "  $lang: $COUNT strings updated"
        TOTAL_UPDATED=$((TOTAL_UPDATED + COUNT))
    else
        ERROR=$(echo "$RESULT" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('errors',[{}])[0].get('detail','unknown error'))" 2>/dev/null || echo "unknown error")
        log_warn "  $lang: $ERROR"
    fi
done
log_info "Autotranslate complete — $TOTAL_UPDATED total strings updated."

# 3. Pull translated files from Weblate API
log_step "Pulling translated files from Weblate..."
python3 << PYEOF
import urllib.request, json, os, sys

TOKEN = "$WEBLATE_TOKEN"
BASE = "$WEBLATE_BASE"
LOCALES_DIR = "$LOCALES_DIR"
LANGS = "$LANGS".split()

for lang in LANGS:
    url = f"{BASE}/translations/junkbin-io/frontend-ui/{lang}/file/"
    req = urllib.request.Request(url, headers={"Authorization": f"Token {TOKEN}"})
    try:
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode())
            path = f"{LOCALES_DIR}/{lang}/translation.json"
            with open(path, 'w') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            print(f"  {lang}: saved")
    except Exception as e:
        print(f"  {lang}: ERROR — {e}", file=sys.stderr)
PYEOF

# 4. Fill remaining empty strings with English fallbacks
log_step "Filling remaining gaps with English fallbacks..."
python3 << PYEOF
import json, os

LOCALES_DIR = "$LOCALES_DIR"
LANGS = "$LANGS".split()

with open(f"{LOCALES_DIR}/en/translation.json") as f:
    en = json.load(f)

def fill_empty(target, source):
    for key, val in source.items():
        if isinstance(val, dict):
            if key not in target or not isinstance(target[key], dict):
                target[key] = {}
            fill_empty(target[key], val)
        elif isinstance(val, str) and (key not in target or target[key] == ''):
            target[key] = val

for lang in LANGS:
    path = f"{LOCALES_DIR}/{lang}/translation.json"
    with open(path) as f:
        data = json.load(f)
    fill_empty(data, en)
    with open(path, 'w') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"  {lang}: gaps filled")
PYEOF

if [ "$DRY_RUN" = true ]; then
    log_warn "Dry run — skipping git commit."
    log_info "Done. Review changes with: git diff frontend/public/locales/"
    exit 0
fi

# 5. Commit and push
log_step "Committing to git..."
git add frontend/public/locales/
if git diff --cached --quiet; then
    log_warn "No changes to commit — translations already up to date."
else
    git commit -m "Sync translations from Weblate MyMemory autotranslate

$(date -u '+%Y-%m-%d %H:%M UTC') — automated sync via sync-translations.sh

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
    git push
    log_info "Pushed to main."
fi

# 6. Reset Weblate to our HEAD so it stays in sync
log_step "Syncing Weblate to HEAD..."
curl -s -X POST \
    -H "Authorization: Token $WEBLATE_TOKEN" \
    -H "Content-Type: application/json" \
    -d '{"operation": "reset"}' \
    "$WEBLATE_BASE/components/$COMPONENT/repository/" > /dev/null
log_info "Weblate synced."

echo ""
log_info "All done. Test on [dev] with ./deployment/update.sh --dev before deploying to [prod]."
