#!/usr/bin/env bash
set -euo pipefail

echo "[Axiom SDA] Setting hostname to 'axiom'..."
sudo hostnamectl set-hostname axiom

echo "[Axiom SDA] Installing Docker & Avahi mDNS..."
sudo apt-get update -y
sudo apt-get install -y avahi-daemon ca-certificates curl
if ! command -v docker >/dev/null 2>&1; then
  curl -fsSL https://get.docker.com | sh
  sudo usermod -aG docker "$USER"
fi

echo "[Axiom SDA] Registering http://axiom.local mDNS service..."
sudo cp provisioning/avahi/axiom.service /etc/avahi/services/axiom.service
sudo systemctl restart avahi-daemon

echo "[Axiom SDA] Starting pinned Axiom stack..."
cp versions.env versions.env.bak
docker compose --env-file versions.env up -d --build

echo "[Axiom SDA] Ready. Open http://axiom.local in your browser."