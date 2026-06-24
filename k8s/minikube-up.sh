#!/usr/bin/env bash
# ============================================================================
# WaiverEdge — Minikube Local Dev Setup
# Starts minikube, builds images, runs migrations, deploys all pods.
#
# Usage:  ./k8s/minikube-up.sh
# ============================================================================
set -euo pipefail
cd "$(dirname "$0")/.."

YELLOW='\033[1;33m'
GREEN='\033[1;32m'
CYAN='\033[1;36m'
NC='\033[0m'

log()  { echo -e "${CYAN}[waiveredge]${NC} $*"; }
ok()   { echo -e "${GREEN}[✓]${NC} $*"; }
warn() { echo -e "${YELLOW}[!]${NC} $*"; }

# ---------- 1. Start minikube if not running ----------
log "Checking minikube status..."
if minikube status --format '{{.Host}}' 2>/dev/null | grep -q Running; then
  ok "Minikube already running"
else
  log "Starting minikube..."
  minikube start --cpus=4 --memory=4096 --driver=docker
  ok "Minikube started"
fi

# ---------- 2. Point docker to minikube's daemon ----------
log "Configuring docker to use minikube..."
eval $(minikube docker-env)
ok "Docker pointing to minikube"

# ---------- 3. Build images ----------
log "Building backend image..."
docker build -t waiveredge-backend:local -f backend/Dockerfile backend/
ok "Backend image built"

log "Building frontend image..."
docker build \
  --build-arg NEXT_PUBLIC_API_BASE=http://localhost:8000 \
  -t waiveredge-frontend:local \
  -f frontend/Dockerfile frontend/
ok "Frontend image built"

# ---------- 4. Create namespace ----------
log "Creating namespace..."
kubectl apply -f k8s/namespace.yaml
ok "Namespace ready"

# ---------- 5. Deploy Postgres ----------
log "Deploying Postgres..."
kubectl apply -f k8s/postgres.yaml
log "Waiting for Postgres pod to be ready..."
kubectl wait --namespace waiveredge \
  --for=condition=ready pod \
  --selector=app=postgres \
  --timeout=120s
ok "Postgres is ready"

# ---------- 5b. Load backend secrets from .env ----------
if [ -f backend/.env ]; then
  log "Loading backend secrets from backend/.env..."
  # Filter out keys already set in the ConfigMap (they point to K8s-internal hosts).
  FILTERED_ENV=$(mktemp)
  grep -v '^\s*#' backend/.env | grep '=' | \
    grep -iv '^DATABASE_URL=' | \
    grep -iv '^CORS_ORIGINS=' | \
    grep -iv '^APP_SECRET=' | \
    grep -iv '^PORT=' | \
    grep -iv '^SEASON=' | \
    grep -iv '^YAHOO_REDIRECT_URI=' \
    > "$FILTERED_ENV" || true
  # Override redirect URI for local dev
  echo "YAHOO_REDIRECT_URI=https://localhost:8000/api/auth/yahoo/callback" >> "$FILTERED_ENV"
  kubectl delete secret backend-secrets --namespace waiveredge --ignore-not-found
  kubectl create secret generic backend-secrets \
    --namespace waiveredge \
    --from-env-file="$FILTERED_ENV"
  rm -f "$FILTERED_ENV"
  ok "Backend secrets loaded"
else
  warn "No backend/.env found — Yahoo OAuth and Stripe will be disabled"
fi

# ---------- 6. Run migrations ----------
log "Creating migrations ConfigMap..."
kubectl delete configmap migrations --namespace waiveredge --ignore-not-found
kubectl create configmap migrations \
  --namespace waiveredge \
  --from-file=backend/migrations/

log "Running migrations job..."
kubectl delete job db-migrate --namespace waiveredge --ignore-not-found
kubectl apply -f k8s/migrations-job.yaml
kubectl wait --namespace waiveredge \
  --for=condition=complete job/db-migrate \
  --timeout=120s
ok "Migrations complete"

# ---------- 7. Deploy backend ----------
log "Deploying backend..."
kubectl apply -f k8s/backend.yaml
kubectl wait --namespace waiveredge \
  --for=condition=ready pod \
  --selector=app=backend \
  --timeout=120s
ok "Backend is ready"

# ---------- 8. Deploy frontend ----------
log "Deploying frontend..."
kubectl apply -f k8s/frontend.yaml
kubectl wait --namespace waiveredge \
  --for=condition=ready pod \
  --selector=app=frontend \
  --timeout=120s
ok "Frontend is ready"

# ---------- 9. Port-forward ----------
log "Setting up port-forwarding..."

# Kill any existing port-forwards for these ports
pkill -f "kubectl port-forward.*8000:8000" 2>/dev/null || true
pkill -f "kubectl port-forward.*3000:3000" 2>/dev/null || true
pkill -f "kubectl port-forward.*5432:5432" 2>/dev/null || true
sleep 1

kubectl port-forward -n waiveredge svc/backend 8000:8000 &
kubectl port-forward -n waiveredge svc/frontend 3000:3000 &
kubectl port-forward -n waiveredge svc/postgres 5432:5432 &

echo ""
echo -e "${GREEN}============================================${NC}"
echo -e "${GREEN} WaiverEdge is running on minikube!${NC}"
echo -e "${GREEN}============================================${NC}"
echo ""
echo -e "  Frontend:  ${CYAN}http://localhost:3000${NC}"
echo -e "  Backend:   ${CYAN}http://localhost:8000${NC}"
echo -e "  Health:    ${CYAN}http://localhost:8000/health${NC}"
echo -e "  Postgres:  ${CYAN}localhost:5432${NC} (user: waiveredge)"
echo ""
echo -e "  Stop:      ${YELLOW}./k8s/minikube-down.sh${NC}"
echo -e "  Logs:      ${YELLOW}kubectl logs -n waiveredge -l app=backend -f${NC}"
echo -e "  Pods:      ${YELLOW}kubectl get pods -n waiveredge${NC}"
echo ""

wait
