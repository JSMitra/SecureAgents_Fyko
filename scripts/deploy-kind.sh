#!/usr/bin/env bash
set -euo pipefail

CLUSTER_NAME="fyko-cluster"

echo "=== 1. Creating KinD Cluster (${CLUSTER_NAME}) ==="
if kind get clusters 2>/dev/null | grep -q "^${CLUSTER_NAME}$"; then
  echo "KinD cluster '${CLUSTER_NAME}' already exists. Skipping creation."
else
  kind create cluster --config kind/kind-config.yaml
fi

echo "=== 2. Building Docker Images locally ==="
docker build -t fyko_server:latest ./fyko_server
docker build -t ann_generator:latest ./ann_generator
docker build -t secret_plan_creator:latest ./fyko_clients -f fyko_clients/secret_plan_creator/Dockerfile
docker build -t secret_plan_reviewer:latest ./fyko_clients -f fyko_clients/secret_plan_reviewer/Dockerfile
docker build -t fyko_ui:latest ./fyko_ui

echo "=== 3. Loading Images into KinD Cluster ==="
kind load docker-image fyko_server:latest --name "${CLUSTER_NAME}"
kind load docker-image ann_generator:latest --name "${CLUSTER_NAME}"
kind load docker-image secret_plan_creator:latest --name "${CLUSTER_NAME}"
kind load docker-image secret_plan_reviewer:latest --name "${CLUSTER_NAME}"
kind load docker-image fyko_ui:latest --name "${CLUSTER_NAME}"

echo "=== 4. Deploying Kubernetes Manifests in Sequential Order ==="
kubectl apply -f k8s/00-namespace.yaml
kubectl apply -f k8s/01-secrets.yaml
kubectl apply -f k8s/02-configmap.yaml
kubectl apply -f k8s/03-postgres.yaml
kubectl apply -f k8s/04-mongodb.yaml
kubectl apply -f k8s/05-rabbitmq.yaml
kubectl apply -f k8s/06-fyko-server.yaml
kubectl apply -f k8s/07-ann-generator.yaml
kubectl apply -f k8s/08-secret-plan-creator.yaml
kubectl apply -f k8s/09-secret-plan-reviewer.yaml
kubectl apply -f k8s/10-fyko-ui.yaml

echo "=== 5. Waiting for Pods to be Ready ==="
kubectl wait --namespace fyko-cluster --for=condition=ready pod --all --timeout=180s || true

echo ""
echo "=== Deployment Completed! ==="
kubectl get pods,svc -n fyko-cluster
echo ""
echo "Access Fyko UI at: http://localhost:3000"

