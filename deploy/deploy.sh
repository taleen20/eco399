#!/usr/bin/env bash
# deploy.sh — sync code to server and (re)start containers
# Safe to run repeatedly. Only changed files are transferred.
#
# Usage: ./deploy.sh <server-host> [ssh-user] [ssh-key]
#
# Example:
#   ./deploy.sh 192.168.1.100
#   ./deploy.sh 192.168.1.100 ubuntu ~/.ssh/my_key.pem

set -euo pipefail

# ── Config ────────────────────────────────────────────────────────────────────
SERVER_HOST="${1:?Usage: $0 <server-host> [ssh-user] [ssh-key]}"
SERVER_USER="${2:-ubuntu}"
SSH_KEY="${3:-}"
APP_DIR="/opt/eco399"

SSH_OPTS="-o StrictHostKeyChecking=accept-new"
[[ -n "$SSH_KEY" ]] && SSH_OPTS="$SSH_OPTS -i $SSH_KEY"
RSYNC_OPTS="-az --delete --progress"
[[ -n "$SSH_KEY" ]] && RSYNC_OPTS="$RSYNC_OPTS -e 'ssh -i $SSH_KEY'"

# Resolve the eco399 root (one level up from this script)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

ssh_run() { ssh $SSH_OPTS "$SERVER_USER@$SERVER_HOST" "$@"; }

# ── Preflight checks ──────────────────────────────────────────────────────────
echo "→ Checking prerequisites ..."

if ! command -v rsync &>/dev/null; then
    echo "  Error: rsync is not installed locally. Install it and retry."
    exit 1
fi

ssh_run "docker compose version" &>/dev/null || {
    echo "  Error: Docker Compose not found on server. Run provision.sh first."
    exit 1
}

echo "  All checks passed."

# ── Sync code ─────────────────────────────────────────────────────────────────
echo "→ Syncing code to $SERVER_HOST:$APP_DIR ..."

rsync -az --delete --progress \
    -e "ssh $SSH_OPTS" \
    --exclude='.git/' \
    --exclude='__pycache__/' \
    --exclude='*.pyc' \
    --exclude='.venv/' \
    --exclude='node_modules/' \
    --exclude='backend/uploads/' \
    --exclude='backend/outputs/' \
    --exclude='backend/test_data/' \
    --exclude='test_results/' \
    --exclude='backend/locustfile.py' \
    "$PROJECT_ROOT/" \
    "$SERVER_USER@$SERVER_HOST:$APP_DIR/"

# ── Start / update containers ─────────────────────────────────────────────────
echo "→ Building and starting containers ..."
ssh_run bash <<REMOTE
set -euo pipefail
cd $APP_DIR

docker compose pull redis 2>/dev/null || true
docker compose build --pull

# Bring up redis and backend first so models load before frontend starts
docker compose up -d redis
docker compose up -d --no-deps backend worker

echo "  Waiting for backend healthcheck (models take ~60s to load) ..."
DEADLINE=\$((SECONDS + 180))
until docker compose ps backend | grep -q "healthy" || [ \$SECONDS -ge \$DEADLINE ]; do
    sleep 5
    echo -n "."
done
echo ""

if ! docker compose ps backend | grep -q "healthy"; then
    echo "  Error: backend did not become healthy in time. Check logs:"
    echo "    docker compose logs backend"
    exit 1
fi

docker compose up -d --no-deps frontend
echo "  All services started."
REMOTE

# ── Summary ───────────────────────────────────────────────────────────────────
echo ""
echo "→ Service status:"
ssh_run "cd $APP_DIR && docker compose ps"

echo ""
echo "✓ Deployment complete. App is running at http://$SERVER_HOST"
