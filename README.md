# Secure AI Agent Interaction using Fyko ANNs: See https://github.com/JSMitra/ForYourKeysOnly

An AI Implementation of my thesis Project explained on YouTube: https://www.youtube.com/watch?v=fJqOqXfSf_M

A multi-agent AI platform that orchestrates **ANN (Artificial Neural Network) request processing** through a pipeline of specialised microservices backed by PostgreSQL, MongoDB, and RabbitMQ.

---

## Architecture

```
                          ┌─────────────────────────────────────────────────────┐
                          │                   fyko-net / fyko-cluster namespace  │
                          │                                                     │
  User ──Browser──► ┌─────┴──────┐                                              │
    (:3000)         │  fyko-ui   │                                              │
                    └─────┬──────┘                                              │
                          │ HTTP (/api/creator, /api/server)                    │
                    ┌─────▼──────┐    AMQP    ┌──────────────┐                 │
                    │fyko-server │ ──────────► │   RabbitMQ   │                 │
                    │  :8000     │             │  :5672/:15672│                 │
                    └─────┬──────┘             └──────┬───────┘                 │
                          │                           │                         │
                    SQL   │                    AMQP   │ (consume)               │
                          ▼                           ▼                         │
                    ┌──────────┐            ┌──────────────────┐                │
                    │PostgreSQL│            │  ann-generator   │                │
                    │  :5432   │            │  (×2 replicas)   │                │
                    └──────────┘            └────────┬─────────┘                │
                                                     │ HTTP callback            │
                    ┌──────────┐                     │                         │
                    │ MongoDB  │◄────────────────────┘                         │
                    │  :27017  │   (plan/review docs)                           │
                    └──────────┘                                                │
                          ▲                                                     │
                          │ MongoDB log                                         │
                    ┌─────┴────────────┐   ┌──────────────────────┐             │
                    │secret-plan-      │   │secret-plan-          │             │
                    │creator  :9001    │◄──│reviewer  :9002       │             │
                    └──────────────────┘   └──────────────────────┘             │
                          │                     ▲ A2A (RSA + ANN AES-256)       │
                          └─────────────────────┘                               │
                          └─────────────────────────────────────────────────────┘
```

---

## Services

| Service | Port | Image | Kind |
|---|---|---|---|
| `postgres` | 5432 | `postgres:15` | StatefulSet |
| `mongodb` | 27017 | `mongo:6` | StatefulSet |
| `rabbitmq` | 5672, 15672 | `rabbitmq:3.12-management` | Deployment |
| `fyko-server` | 8000 | `fyko_server:latest` | Deployment (1) |
| `ann-generator` | — | `ann_generator:latest` | StatefulSet (2) |
| `secret-plan-creator` | 9001 | `secret_plan_creator:latest` | Deployment (1) |
| `secret-plan-reviewer` | 9002 | `secret_plan_reviewer:latest` | Deployment (1) |
| `fyko-ui` | 3000 | `fyko_ui:latest` | Deployment (1) / NodePort 30080 |

---

## Quick Start

### Docker Compose (local dev)

```bash
# 1. Copy and fill in secrets
cp .env.example .env
#    edit .env — set GEMINI_API_KEY at minimum

# 2. Build local images and start everything
docker compose up --build

# 3. Verify
curl http://localhost:8000/health

# 4. Open Interactive Agent Web UI
open http://localhost:3000

# RabbitMQ management UI
open http://localhost:15672   # user: fyko  pass: fykopass
```

### Kubernetes with KinD (Recommended)

You can run the all-in-one deploy script:
```bash
./scripts/deploy-kind.sh
```

Or step-by-step:
```bash
# 1. Create KinD cluster with port mapping (maps NodePort 30080 to localhost:3000)
kind create cluster --config k8s/kind-config.yaml

# 2. Build local docker images
docker build -t fyko_server:latest          ./fyko_server
docker build -t ann_generator:latest        ./ann_generator
docker build -t secret_plan_creator:latest  ./fyko_clients -f fyko_clients/secret_plan_creator/Dockerfile
docker build -t secret_plan_reviewer:latest ./fyko_clients -f fyko_clients/secret_plan_reviewer/Dockerfile
docker build -t fyko_ui:latest              ./fyko_ui

# 3. Load images into the KinD cluster
kind load docker-image fyko_server:latest --name fyko-cluster
kind load docker-image ann_generator:latest --name fyko-cluster
kind load docker-image secret_plan_creator:latest --name fyko-cluster
kind load docker-image secret_plan_reviewer:latest --name fyko-cluster
kind load docker-image fyko_ui:latest --name fyko-cluster

# 4. Apply all manifests (flat numbered structure applies in exact order)
kubectl apply -f k8s/

# Or apply sequentially:
# kubectl apply -f k8s/00-namespace.yaml
# kubectl apply -f k8s/01-secrets.yaml
# kubectl apply -f k8s/02-configmap.yaml
# kubectl apply -f k8s/03-postgres.yaml
# kubectl apply -f k8s/04-mongodb.yaml
# kubectl apply -f k8s/05-rabbitmq.yaml
# kubectl apply -f k8s/06-fyko-server.yaml
# kubectl apply -f k8s/07-ann-generator.yaml
# kubectl apply -f k8s/08-secret-plan-creator.yaml
# kubectl apply -f k8s/09-secret-plan-reviewer.yaml
# kubectl apply -f k8s/10-fyko-ui.yaml

# 5. Check status
kubectl -n fyko-cluster get pods -w

# 6. Open UI directly
open http://localhost:3000
```

### Kubernetes (Minikube / Generic Cluster)

```bash
# 1. Ensure local images are available to the cluster
#    For minikube:
eval $(minikube docker-env)
docker build -t fyko_server:latest          ./fyko_server
docker build -t ann_generator:latest        ./ann_generator
docker build -t secret_plan_creator:latest  ./fyko_clients -f fyko_clients/secret_plan_creator/Dockerfile
docker build -t secret_plan_reviewer:latest ./fyko_clients -f fyko_clients/secret_plan_reviewer/Dockerfile
docker build -t fyko_ui:latest              ./fyko_ui

# 2. Apply all manifests
kubectl apply -f k8s/

# 3. Check rollout
kubectl -n fyko-cluster get pods -w

# 4. Forward fyko-server locally (optional)
kubectl -n fyko-cluster port-forward svc/fyko-server 8000:8000
```

---

## Environment Setup

Copy `.env.example` to `.env` and update the values:

```
POSTGRES_PASSWORD=fykopass      # password for PostgreSQL
MONGO_PASSWORD=fykopass         # password for MongoDB
RABBITMQ_PASSWORD=fykopass      # password for RabbitMQ
GEMINI_API_KEY=<your key>       # Google Gemini API key
```

> **Note:** The Kubernetes `Secret` in `k8s/secrets.yaml` also contains a `GEMINI_API_KEY` placeholder — replace `YOUR_GEMINI_API_KEY_HERE` before applying to a real cluster. Never commit real secrets to version control.

---

## API Reference

### Fyko Server (`http://localhost:8000`)

| Method | Path | Description |
|---|---|---|
| `GET` | `/health` | Liveness / readiness check |
| `POST` | `/ann/request` | Submit a new ANN request |
| `GET` | `/ann/request/{ulid}` | Get status of an ANN request |
| `GET` | `/ann/requests` | List all ANN requests |
| `POST` | `/internal/callback` | Internal callback from ann-generator |

### Secret Plan Creator (`http://localhost:9001`)

| Method | Path | Description |
|---|---|---|
| `GET` | `/health` | Health check |
| `POST` | `/create` | Generate a new secret plan |

### Secret Plan Reviewer (`http://localhost:9002`)

| Method | Path | Description |
|---|---|---|
| `GET` | `/health` | Health check |
| `POST` | `/review` | Review a generated secret plan |

---

## Project Structure

```
SecureAgents_Fyko/
├── fyko_server/          # FastAPI server — REST API + RabbitMQ publisher
├── ann_generator/        # Worker — consumes RabbitMQ, runs ANN inference
├── fyko_clients/         # Agent clients (creator & reviewer)
│   ├── shared/           # Cryptography & FYKO ANN key helpers
│   ├── secret_plan_creator/
│   └── secret_plan_reviewer/
├── fyko_ui/              # React 18 + Tailwind spy dashboard UI
├── kind/
│   └── kind-config.yaml  # KinD cluster port mapping configuration
├── k8s/                  # Flat numbered Kubernetes manifests (namespace: fyko-cluster)
│   ├── 00-namespace.yaml
│   ├── 01-secrets.yaml
│   ├── 02-configmap.yaml
│   ├── 03-postgres.yaml
│   ├── 04-mongodb.yaml
│   ├── 05-rabbitmq.yaml
│   ├── 06-fyko-server.yaml
│   ├── 07-ann-generator.yaml
│   ├── 08-secret-plan-creator.yaml
│   ├── 09-secret-plan-reviewer.yaml
│   └── 10-fyko-ui.yaml
├── scripts/
│   └── deploy-kind.sh    # Automated KinD cluster build & deploy script
├── sql/
│   └── init.sql          # PostgreSQL DDL for docker-compose
├── docker-compose.yaml   # Local development stack
├── .env.example          # Environment variable template
└── README.md
```
