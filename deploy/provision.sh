#!/usr/bin/env bash
# provision.sh — one-time server setup
# Run this once on a fresh Ubuntu 22.04/24.04 server before deploying.
# Usage: ./provision.sh <server-host> [ssh-user] [ssh-key]
#
# Example:
#   ./provision.sh 192.168.1.100
#   ./provision.sh 192.168.1.100 ubuntu ~/.ssh/my_key.pem

set -euo pipefail

# ── Config ────────────────────────────────────────────────────────────────────
SERVER_HOST="${1:?Usage: $0 <server-host> [ssh-user] [ssh-key]}"
SERVER_USER="${2:-ubuntu}"
SSH_KEY="${3:-}"
APP_DIR="/opt/eco399"

SSH_OPTS="-o StrictHostKeyChecking=accept-new"
[[ -n "$SSH_KEY" ]] && SSH_OPTS="$SSH_OPTS -i $SSH_KEY"

ssh_run() { ssh $SSH_OPTS "$SERVER_USER@$SERVER_HOST" "$@"; }

# ── Preflight ─────────────────────────────────────────────────────────────────
echo "→ Testing SSH connection to $SERVER_USER@$SERVER_HOST ..."
ssh_run "echo '  Connected OK'"

# ── Install Docker CE ─────────────────────────────────────────────────────────
echo "→ Installing Docker CE ..."
ssh_run bash <<'REMOTE'
set -euo pipefail
if command -v docker &>/dev/null; then
    echo "  Docker already installed: $(docker --version)"
    exit 0
fi

apt-get update -qq
apt-get install -y --no-install-recommends ca-certificates curl gnupg

install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg \
    | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
chmod a+r /etc/apt/keyrings/docker.gpg

echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" \
    | tee /etc/apt/sources.list.d/docker.list >/dev/null

apt-get update -qq
apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

systemctl enable --now docker
echo "  Docker installed: $(docker --version)"
REMOTE

# ── Add user to docker group ──────────────────────────────────────────────────
echo "→ Adding $SERVER_USER to docker group ..."
ssh_run "sudo usermod -aG docker $SERVER_USER || true"

# ── Fix Docker DNS ────────────────────────────────────────────────────────────
# Ubuntu's systemd-resolved uses 127.0.0.53 which is unreachable inside
# Docker containers. Point Docker at real upstream DNS instead.
echo "→ Configuring Docker DNS ..."
ssh_run bash <<'REMOTE'
set -euo pipefail
UPSTREAM=$(resolvectl status 2>/dev/null | awk '/DNS Servers:/{print $3; exit}')
DNS1="${UPSTREAM:-8.8.8.8}"
cat > /etc/docker/daemon.json <<EOF
{
    "dns": ["$DNS1", "8.8.8.8", "1.1.1.1"],
    "log-driver": "json-file",
    "log-opts": { "max-size": "10m", "max-file": "3" }
}
EOF
systemctl restart docker
echo "  Docker DNS set to: $DNS1 8.8.8.8 1.1.1.1"
REMOTE

# ── Firewall ──────────────────────────────────────────────────────────────────
echo "→ Configuring UFW firewall ..."
ssh_run bash <<'REMOTE'
set -euo pipefail
apt-get install -y --no-install-recommends ufw >/dev/null
ufw --force reset >/dev/null
ufw default deny incoming
ufw default allow outgoing
ufw allow 22/tcp   comment 'SSH'
ufw allow 80/tcp   comment 'HTTP'
ufw allow 443/tcp  comment 'HTTPS'
ufw --force enable
echo "  UFW status:"
ufw status numbered
REMOTE

# ── App directory ─────────────────────────────────────────────────────────────
echo "→ Creating app directory $APP_DIR ..."
ssh_run "sudo mkdir -p $APP_DIR && sudo chown $SERVER_USER:$SERVER_USER $APP_DIR"

# ── Done ──────────────────────────────────────────────────────────────────────
echo ""
echo "✓ Server provisioned successfully."
echo "  Next: run ./deploy.sh $SERVER_HOST $SERVER_USER ${SSH_KEY:-(default key)}"
