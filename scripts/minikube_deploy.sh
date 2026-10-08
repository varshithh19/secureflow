#!/usr/bin/env bash
# ==============================================================================
# SecureFlow Minikube Local Cluster Deployment Script
# ==============================================================================
set -euo pipefail

echo "[*] Step 1: Configuring Minikube Docker Environment..."
eval $(minikube docker-env || true)

echo "[*] Step 2: Building SecureFlow hardened container image..."
docker build -t ghcr.io/varshith/secureflow:1.0.0 -f docker/Dockerfile .

echo "[*] Step 3: Applying Kubernetes Manifests..."
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/configmap.yaml

# If secret does not exist, initialize from example
if ! kubectl get secret secureflow-secrets -n secureflow >/dev/null 2>&1; then
    echo "[*] Creating placeholder secret in namespace 'secureflow'..."
    kubectl apply -f k8s/secret.example.yaml
fi

kubectl apply -f k8s/postgres.yaml
kubectl apply -f k8s/service.yaml
kubectl apply -f k8s/deployment.yaml

echo "[*] Step 4: Waiting for PostgreSQL rollout..."
kubectl rollout status statefulset/secureflow-postgres -n secureflow --timeout=120s

echo "[*] Step 5: Waiting for Application rollout..."
kubectl rollout status deployment/secureflow-app -n secureflow --timeout=120s

echo "[*] SecureFlow deployment completed successfully!"
echo "[*] Pod Status:"
kubectl get pods -n secureflow
