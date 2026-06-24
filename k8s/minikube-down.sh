#!/usr/bin/env bash
# ============================================================================
# WaiverEdge — Minikube Teardown
# Stops port-forwards and deletes all K8s resources. Keeps minikube running.
#
# Usage:  ./k8s/minikube-down.sh [--full]
#   --full  also stops minikube itself
# ============================================================================
set -euo pipefail

RED='\033[1;31m'
GREEN='\033[1;32m'
CYAN='\033[1;36m'
NC='\033[0m'

log() { echo -e "${CYAN}[waiveredge]${NC} $*"; }
ok()  { echo -e "${GREEN}[✓]${NC} $*"; }

# Kill port-forwards
log "Stopping port-forwards..."
pkill -f "kubectl port-forward.*waiveredge" 2>/dev/null || true
ok "Port-forwards stopped"

# Delete namespace (removes everything)
log "Deleting waiveredge namespace..."
kubectl delete namespace waiveredge --ignore-not-found --wait=false
ok "Namespace deleted"

if [[ "${1:-}" == "--full" ]]; then
  log "Stopping minikube..."
  minikube stop
  ok "Minikube stopped"
fi

echo ""
echo -e "${GREEN}WaiverEdge cleaned up.${NC}"
echo -e "  Restart:  ${CYAN}./k8s/minikube-up.sh${NC}"
echo ""
