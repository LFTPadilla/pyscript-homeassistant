#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
HA_CONFIG="${HA_CONFIG:-$HOME/.config/home-assistant/config.json}"
DEFAULT_VERIFY_ENTITY="${VERIFY_ENTITY:-media_player.google_speaker}"

usage() {
  cat <<'EOF'
Usage: ./scripts/deploy.sh [--message "commit message"] [--verify-entity entity_id] [--verify-only]

Options:
  --message        Commit message to use when there are local changes.
  --verify-entity  Entity to query after pull/reload. Default: media_player.google_speaker
  --verify-only    Skip git commit/push and only run HA pull/reload verification.
  -h, --help       Show this help.
EOF
}

require_cmd() {
  command -v "$1" >/dev/null 2>&1 || {
    echo "Missing required command: $1" >&2
    exit 1
  }
}

log() {
  printf '[deploy] %s\n' "$*"
}

MESSAGE=""
VERIFY_ENTITY="$DEFAULT_VERIFY_ENTITY"
VERIFY_ONLY="false"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --message)
      MESSAGE="${2:-}"
      shift 2
      ;;
    --verify-entity)
      VERIFY_ENTITY="${2:-}"
      shift 2
      ;;
    --verify-only)
      VERIFY_ONLY="true"
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage >&2
      exit 1
      ;;
  esac
done

require_cmd git
require_cmd jq
require_cmd curl

if [[ ! -f "$HA_CONFIG" ]]; then
  echo "Home Assistant config not found: $HA_CONFIG" >&2
  exit 1
fi

HA_URL="$(jq -r '.url' "$HA_CONFIG")"
HA_TOKEN="$(jq -r '.token' "$HA_CONFIG")"

if [[ -z "$HA_URL" || "$HA_URL" == "null" || -z "$HA_TOKEN" || "$HA_TOKEN" == "null" ]]; then
  echo "Home Assistant config is missing url/token in $HA_CONFIG" >&2
  exit 1
fi

api_post() {
  local endpoint="$1"
  curl --fail --silent --show-error \
    -X POST "${HA_URL%/}/api/${endpoint}" \
    -H "Authorization: Bearer $HA_TOKEN" \
    -H "Content-Type: application/json" \
    -d '{}'
}

api_get() {
  local endpoint="$1"
  curl --fail --silent --show-error \
    "${HA_URL%/}/api/${endpoint}" \
    -H "Authorization: Bearer $HA_TOKEN"
}

cd "$REPO_DIR"

if [[ "$VERIFY_ONLY" != "true" ]]; then
  BRANCH="$(git branch --show-current)"
  STATUS="$(git status --short)"

  log "repo: $REPO_DIR"
  log "branch: ${BRANCH:-unknown}"

  if [[ -n "$STATUS" ]]; then
    if [[ -z "$MESSAGE" ]]; then
      MESSAGE="Update Home Assistant pyscripts"
    fi
    log "staging changes"
    git add -A
    log "committing: $MESSAGE"
    git commit -m "$MESSAGE"
    log "pushing to origin/${BRANCH:-HEAD}"
    git push origin HEAD
  else
    log "no local changes to commit"
  fi
fi

log "calling shell_command.pull_pyscripts"
PULL_RESPONSE="$(api_post 'services/shell_command/pull_pyscripts')"
log "pull response: ${PULL_RESPONSE:-[]}"

log "calling pyscript.reload"
RELOAD_RESPONSE="$(api_post 'services/pyscript/reload')"
log "reload response: ${RELOAD_RESPONSE:-[]}"

log "verifying Home Assistant state"
STATE_JSON="$(api_get "states/${VERIFY_ENTITY}")"
STATE_VALUE="$(printf '%s' "$STATE_JSON" | jq -r '.state')"
FRIENDLY_NAME="$(printf '%s' "$STATE_JSON" | jq -r '.attributes.friendly_name // .entity_id')"

log "verified entity: ${FRIENDLY_NAME} (${VERIFY_ENTITY})"
log "verified state: ${STATE_VALUE}"

log "checking pyscript integration availability"
PYSCRIPT_STATE="$(api_get 'config/config_entries/entry' | jq -r '.[] | select(.domain=="pyscript") | .state' | head -n1)"
if [[ -n "$PYSCRIPT_STATE" ]]; then
  log "pyscript integration state: $PYSCRIPT_STATE"
fi

log "deploy finished"
