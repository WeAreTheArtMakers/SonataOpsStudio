#!/usr/bin/env bash
set -euo pipefail

APP_DIR="${APP_DIR:-/opt/sonataops-studio}"
BRANCH="${BRANCH:-main}"

cd "$APP_DIR"

git fetch origin "$BRANCH"
git checkout "$BRANCH"
git pull --ff-only origin "$BRANCH"

docker compose -f docker-compose.yml -f docker-compose.cloud.yml up -d --build

echo "Update completed"
