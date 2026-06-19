#!/usr/bin/env bash
# up.sh - Idempotent Local Multi-Node Cluster Orchestrator

# Exit immediately if a command exits with a non-zero status
set -e

CLUSTER_NAME="ckad-docker"
NAMESPACE="lab-pack"
APP_IMAGE="fastapi:v7"

echo "🚀 Booting Minikube nodes with resource profiles..."
# Passing hardware specs ensures a proper scratch build, while remaining safe for warm reboots
minikube start \
  -p "$CLUSTER_NAME" \
  --nodes=2 \
  --driver=docker \
  --kubernetes-version=v1.35.1 \
  --cpus=2 \
  --memory=4000 \
  --cache-images=false

echo "⏳ Waiting for cluster control plane to stabilize..."
kubectl wait --for=condition=Ready nodes --all --timeout=90s

# --- Local Image Sourcing ---
echo "📦 Verifying local image availability inside cluster namespaces..."
# Checks if the image tag is already cached inside Minikube's image cache table
if ! minikube image ls -p "$CLUSTER_NAME" | grep -q "$APP_IMAGE"; then
    echo "📥 Image '$APP_IMAGE' not found in cluster cache. Transporting image layers..."
    minikube image load "$APP_IMAGE" -p "$CLUSTER_NAME"
    echo "✅ Image successfully loaded into cluster daemon registries."
else
    echo "✅ Image '$APP_IMAGE' is already cached on cluster nodes. Skipping..."
fi

# --- Infrastructure Addons Layer ---
echo "⚙️ Validating core platform addons..."

# Handle NGINX Ingress Natively
if ! minikube addons list -p "$CLUSTER_NAME" | grep -q "ingress.*enabled"; then
    echo "📦 Ingress addon not active. Enabling NGINX Ingress Controller..."
    minikube addons enable ingress -p "$CLUSTER_NAME"
    
    echo "⏳ Waiting for Ingress controller webhook components to initialize..."
    # This prevents race conditions where application manifests apply before the webhook is ready
    sleep 20 
else
    echo "✅ Ingress addon is already active."
fi

# Handle Metrics Server Natively
if ! minikube addons list -p "$CLUSTER_NAME" | grep -q "metrics-server.*enabled"; then
    echo "📊 Metrics Server not active. Enabling Native Engine..."
    minikube addons enable metrics-server -p "$CLUSTER_NAME"
    
    echo "🛠️ Patching metrics-server to accept local self-signed certificates..."
    kubectl patch deployment metrics-server -n kube-system --type='json' -p='[
      {"op": "add", "path": "/spec/template/spec/containers/0/args/-", "value": "--kubelet-insecure-tls"}
    ]'
else
    echo "✅ Metrics Server addon is already active."
fi

# --- Workload & Patch Execution Layer ---
echo "🛠️ Enforcing declarative cluster-level infrastructure overrides..."
kubectl apply -k cluster-config/

echo "🔄 Flushing network overlay states to ensure clean cross-namespace routing..."
kubectl rollout restart daemonset/kindnet -n kube-system
kubectl rollout restart deployment/coredns -n kube-system

echo "⏳ Giving network controllers a brief window to align..."
sleep 10

echo "📦 Provisioning application stack workloads..."
# Ensure namespace creation is explicitly executed first
if [ -f ns.yaml ]; then kubectl apply -f ns.yaml; fi
if [ -f secret/secret.yaml ]; then kubectl apply -f secret/secret.yaml; fi

kubectl apply -f db.yaml
kubectl apply -f api.yaml
kubectl apply -f platform-network/ingress.yaml
kubectl apply -f platform-network/network-policy.yaml
echo "🎯 Tuning local workspace focus rules..."
kubectl config set-context ckad-docker --namespace=$NAMESPACE

echo "================================================================="
echo "✅ SUCCESS: Cluster state has successfully normalized!"
echo "👉 Run: 'kubectl get pods -A' to monitor final status transitions."
echo "================================================================="