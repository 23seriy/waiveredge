#!/usr/bin/env bash
# ============================================================================
# WaiverEdge — Rebuild & Redeploy a single service
#
# Usage:  ./k8s/rebuild.sh backend    # rebuild backend only
#         ./k8s/rebuild.sh frontend   # rebuild frontend only
#         ./k8s/rebuild.sh all        # rebuild both
# ============================================================================
set -euo pipefail
cd "$(dirname "$0")/.."

CYAN='\033[1;36m'
GREEN='\033[1;32m'
NC='\033[0m'

log() { echo -e "${CYAN}[waiveredge]${NC} $*"; }
ok()  { echo -e "${GREEN}[✓]${NC} $*"; }

eval $(minikube docker-env)

TARGET="${1:-all}"

if [[ "$TARGET" == "backend" || "$TARGET" == "all" ]]; then
  log "Rebuilding backend image..."
  docker build -t waiveredge-backend:local -f backend/Dockerfile backend/
  kubectl rollout restart deployment/backend -n waiveredge
  kubectl wait --namespace waiveredge --for=condition=ready pod --selector=app=backend --timeout=120s
  ok "Backend redeployed"
fi

if [[ "$TARGET" == "frontend" || "$TARGET" == "all" ]]; then
  log "Rebuilding frontend image..."
  docker build \
    --build-arg NEXT_PUBLIC_API_BASE=http://localhost:8000 \
    -t waiveredge-frontend:local \
    -f frontend/Dockerfile frontend/
  kubectl rollout restart deployment/frontend -n waiveredge
  kubectl wait --namespace waiveredge --for=condition=ready pod --selector=app=frontend --timeout=120s
  ok "Frontend redeployed"
fi

if [[ "$TARGET" == "migrate" ]]; then
  log "Re-running migrations..."
  kubectl delete configmap migrations --namespace waiveredge --ignore-not-found
  kubectl create configmap migrations --namespace waiveredge --from-file=backend/migrations/
  kubectl delete job db-migrate --namespace waiveredge --ignore-not-found
  kubectl apply -f k8s/migrations-job.yaml
  kubectl wait --namespace waiveredge --for=condition=complete job/db-migrate --timeout=120s
  ok "Migrations re-applied"
fi

echo -e "${GREEN}Done.${NC}"
