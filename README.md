# SecureAgents Fyko : See https://github.com/JSMitra/ForYourKeysOnly

An AI Implementation of my thesis Project explained on YouTube: https://www.youtube.com/watch?v=fJqOqXfSf_M

A multi-agent AI platform that orchestrates **ANN (Artificial Neural Network) request processing** through a pipeline of specialised microservices backed by PostgreSQL, MongoDB, and RabbitMQ.

---

## Architecture

```
                          ┌─────────────────────────────────────────────────────┐
                          │                   fyko-net / fyko namespace          │
                          │                                                     │
  Client ──HTTP──►  ┌─────┴──────┐    AMQP    ┌──────────────┐                 │
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
                                                                                │
                    ┌──────────────────┐   ┌──────────────────────┐             │
                    │secret-plan-      │   │secret-plan-          │             │
                    │creator  :9001    │◄──│reviewer  :9002       │             │
                    └──────────────────┘   └──────────────────────┘             │
                          │                                                     │
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

# RabbitMQ management UI
open http://localhost:15672   # user: fyko  pass: fykopass
```

### Kubernetes (minikube / any cluster)

```bash
# 1. Ensure local images are available to the cluster
#    For minikube:
eval $(minikube docker-env)
docker build -t fyko_server:latest       ./fyko_server
docker build -t ann_generator:latest     ./ann_generator
docker build -t secret_plan_creator:latest ./fyko_clients -f fyko_clients/Dockerfile.creator
docker build -t secret_plan_reviewer:latest ./fyko_clients -f fyko_clients/Dockerfile.reviewer

# 2. Apply manifests in dependency order
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/secrets.yaml
kubectl apply -f k8s/configmap.yaml

kubectl apply -f k8s/postgres/init-configmap.yaml
kubectl apply -f k8s/postgres/pvc.yaml
kubectl apply -f k8s/postgres/statefulset.yaml
kubectl apply -f k8s/postgres/service.yaml

kubectl apply -f k8s/mongodb/pvc.yaml
kubectl apply -f k8s/mongodb/statefulset.yaml
kubectl apply -f k8s/mongodb/service.yaml

kubectl apply -f k8s/rabbitmq/deployment.yaml
kubectl apply -f k8s/rabbitmq/service.yaml

kubectl apply -f k8s/fyko_server/deployment.yaml
kubectl apply -f k8s/fyko_server/service.yaml

kubectl apply -f k8s/ann_generator/statefulset.yaml

kubectl apply -f k8s/secret_plan_creator/deployment.yaml
kubectl apply -f k8s/secret_plan_creator/service.yaml

kubectl apply -f k8s/secret_plan_reviewer/deployment.yaml
kubectl apply -f k8s/secret_plan_reviewer/service.yaml

# 3. Check rollout
kubectl -n fyko get pods -w

# 4. Forward fyko-server locally
kubectl -n fyko port-forward svc/fyko-server 8000:8000
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
│   └── shared/           # Shared fyko_ann helper
├── k8s/                  # Kubernetes manifests (namespace: fyko)
│   ├── namespace.yaml
│   ├── configmap.yaml
│   ├── secrets.yaml
│   ├── postgres/
│   ├── mongodb/
│   ├── rabbitmq/
│   ├── fyko_server/
│   ├── ann_generator/
│   ├── secret_plan_creator/
│   └── secret_plan_reviewer/
├── docker-compose.yaml   # Local development stack
├── .env.example          # Environment variable template
└── README.md
```
