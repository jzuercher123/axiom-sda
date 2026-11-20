#!/usr/bin/env bash
set -euo pipefail

if [ ! -f versions.env.bak ]; then
  echo "No backup versions.env.bak found. Cannot roll back."
  exit 1
fi

echo "[Axiom SDA] Rolling back to previous pinned release..."
cp versions.env.bak versions.env
docker compose --env-file versions.env up -d
echo "[Axiom SDA] Rollback complete."