#!/usr/bin/env bash
set -euo pipefail

REPO_URL="${REPO_URL:-https://github.com/WeAreTheArtMakers/SonataOpsStudio.git}"
BRANCH="${BRANCH:-main}"
APP_DIR="${APP_DIR:-/opt/sonataops-studio}"
SONATA_DOMAIN="${SONATA_DOMAIN:-localhost}"

require_cmd() {
  command -v "$1" >/dev/null 2>&1
}

set_env() {
  local key="$1"
  local value="$2"
  if grep -q "^${key}=" .env; then
    sed -i.bak "s|^${key}=.*|${key}=${value}|" .env
  else
    echo "${key}=${value}" >> .env
  fi
}

if ! require_cmd git; then
  sudo apt-get update
  sudo apt-get install -y git ca-certificates curl
fi

if ! require_cmd docker; then
  curl -fsSL https://get.docker.com | sudo sh
  sudo usermod -aG docker "${SUDO_USER:-$USER}" || true
fi

if ! docker compose version >/dev/null 2>&1; then
  sudo apt-get update
  sudo apt-get install -y docker-compose-plugin
fi

sudo mkdir -p "$(dirname "$APP_DIR")"
if [ ! -d "$APP_DIR/.git" ]; then
  sudo git clone --depth=1 --branch "$BRANCH" "$REPO_URL" "$APP_DIR"
else
  sudo git -C "$APP_DIR" fetch origin "$BRANCH"
  sudo git -C "$APP_DIR" checkout "$BRANCH"
  sudo git -C "$APP_DIR" pull --ff-only origin "$BRANCH"
fi

sudo chown -R "${SUDO_USER:-$USER}:${SUDO_USER:-$USER}" "$APP_DIR"
cd "$APP_DIR"

cp -n .env.example .env
set_env NEXT_PUBLIC_API_BASE_URL /api
set_env BACKEND_INTERNAL_URL http://backend-api:8000
set_env SONATA_DOMAIN "$SONATA_DOMAIN"
if [ "$SONATA_DOMAIN" != "localhost" ]; then
  set_env PUBLIC_API_URL "https://${SONATA_DOMAIN}"
fi

sudo docker compose -f docker-compose.yml -f docker-compose.cloud.yml up -d --build

sleep 20
if curl -fsS http://127.0.0.1/api/health >/dev/null 2>&1; then
  echo "SonataOps is healthy at http://${SONATA_DOMAIN}"
else
  echo "SonataOps started but health endpoint did not return success yet."
fi
