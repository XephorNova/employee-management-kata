# ACME HR Salary Management — Infrastructure Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Containerize the backend and frontend for local Docker Compose development and GCP deployment (Cloud Run + Firebase Hosting).

**Prerequisite:** Backend plan (`2026-06-15-backend.md`) and Frontend plan (`2026-06-15-frontend.md`) must be complete.

**Tech Stack:** Docker, Docker Compose, GCP Cloud Run, Firebase Hosting, GCP Secret Manager

---

## File Map

```
product-recommender/
  backend/
    Dockerfile
  frontend/
    Dockerfile
    nginx.conf
  docker-compose.yml
  .env.example
  deploy/
    deploy-backend.sh
    deploy-frontend.sh
    cloudbuild.yaml
```

---

### Task 1: Backend Dockerfile

**Files:**
- Create: `backend/Dockerfile`

- [ ] **Step 1: Write failing smoke test (pre-flight check)**

Before building, verify the backend runs locally:

```bash
cd backend && source .venv/bin/activate && uvicorn app.main:app --port 8000 &
curl -s http://localhost:8000/health | grep '"status":"ok"'
kill %1
```

Expected: `{"status":"ok"}` returned successfully.

- [ ] **Step 2: Create `backend/Dockerfile`**

```dockerfile
FROM python:3.12-slim

WORKDIR /app

# Install system dependencies for bcrypt
RUN apt-get update && apt-get install -y --no-install-recommends gcc libffi-dev && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8080

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
```

- [ ] **Step 3: Build the Docker image**

```bash
cd backend && docker build -t acme-hr-backend:local .
```

Expected: Image builds successfully. Final line: `Successfully tagged acme-hr-backend:local`

- [ ] **Step 4: Run the container and verify**

```bash
docker run -d --name acme-backend-test -p 8080:8080 \
  -e DATABASE_URL=sqlite+aiosqlite:///./acme_hr.db \
  -e SECRET_KEY=test-secret-do-not-use-in-prod \
  acme-hr-backend:local

# Wait for startup
sleep 3
curl -s http://localhost:8080/health
docker stop acme-backend-test && docker rm acme-backend-test
```

Expected: `{"status":"ok"}`

- [ ] **Step 5: Commit**

```bash
git add backend/Dockerfile && git commit -m "feat: add backend Dockerfile for Python 3.12 FastAPI"
```

---

### Task 2: Frontend Dockerfile + nginx config

**Files:**
- Create: `frontend/Dockerfile`
- Create: `frontend/nginx.conf`

- [ ] **Step 1: Create `frontend/nginx.conf`**

```nginx
server {
    listen 80;
    root /usr/share/nginx/html;
    index index.html;

    # API proxy to backend (used in Docker Compose; in GCP, frontend is static)
    location /auth/ {
        proxy_pass http://backend:8080;
        proxy_set_header Host $host;
    }

    location /api/ {
        proxy_pass http://backend:8080;
        proxy_set_header Host $host;
    }

    # SPA fallback: all other routes serve index.html
    location / {
        try_files $uri $uri/ /index.html;
    }
}
```

- [ ] **Step 2: Create `frontend/Dockerfile`**

```dockerfile
# Build stage
FROM node:20-alpine AS build

WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

# Production stage
FROM nginx:alpine

COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
```

- [ ] **Step 3: Build and verify**

```bash
cd frontend && docker build -t acme-hr-frontend:local .
```

Expected: Multi-stage build completes. Image size should be under 50MB.

- [ ] **Step 4: Commit**

```bash
git add frontend/Dockerfile frontend/nginx.conf && git commit -m "feat: add frontend multi-stage Dockerfile with nginx reverse proxy"
```

---

### Task 3: Docker Compose for local development

**Files:**
- Create: `docker-compose.yml`
- Create: `.env.example`

- [ ] **Step 1: Create `.env.example`**

```bash
# Copy to .env and fill in values
DATABASE_URL=sqlite+aiosqlite:///./acme_hr.db
SECRET_KEY=change-me-in-production-min-32-chars
ANTHROPIC_API_KEY=sk-ant-...
```

- [ ] **Step 2: Create `docker-compose.yml`**

```yaml
version: "3.9"

services:
  backend:
    build:
      context: ./backend
    env_file: .env
    ports:
      - "8000:8080"
    volumes:
      # Persist SQLite database across restarts
      - ./data:/app/data
    environment:
      DATABASE_URL: sqlite+aiosqlite:////app/data/acme_hr.db
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8080/health"]
      interval: 10s
      timeout: 5s
      retries: 3
      start_period: 15s

  frontend:
    build:
      context: ./frontend
    ports:
      - "5173:80"
    depends_on:
      backend:
        condition: service_healthy

volumes:
  data:
```

- [ ] **Step 3: Create the data directory**

```bash
mkdir -p data
echo "data/*.db" >> .gitignore
```

- [ ] **Step 4: Start the full stack**

```bash
docker compose up --build -d
```

Expected: Both containers start. Backend healthcheck passes within 30s.

- [ ] **Step 5: Seed the database inside the container**

```bash
docker compose exec backend python seed.py
```

Expected: 10,000 employees seeded. Output ends with credentials.

- [ ] **Step 6: Verify the stack**

```bash
# Backend health
curl http://localhost:8000/health

# Login via API
curl -s -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@acme.com","password":"Admin123!"}' | python3 -m json.tool

# Frontend loads
curl -sI http://localhost:5173 | grep "200 OK"
```

Expected: All three checks pass.

- [ ] **Step 7: Stop the stack**

```bash
docker compose down
```

- [ ] **Step 8: Commit**

```bash
git add docker-compose.yml .env.example data/.gitkeep .gitignore && git commit -m "feat: add Docker Compose for local full-stack development"
```

---

### Task 4: GCP Cloud Run deployment (backend)

**Files:**
- Create: `deploy/deploy-backend.sh`

- [ ] **Step 1: Prerequisites check**

Run these to verify GCP tooling is available:

```bash
gcloud --version
gcloud auth print-access-token > /dev/null && echo "Authenticated"
gcloud config get-value project
```

Expected: All commands succeed. Note your project ID.

- [ ] **Step 2: Enable required GCP APIs**

```bash
PROJECT_ID=$(gcloud config get-value project)
gcloud services enable run.googleapis.com containerregistry.googleapis.com secretmanager.googleapis.com --project "$PROJECT_ID"
```

- [ ] **Step 3: Store secrets in Secret Manager**

```bash
# Replace with your actual values
echo -n "your-super-secret-jwt-key-min-32-chars" | gcloud secrets create acme-hr-secret-key --data-file=-
echo -n "sk-ant-your-actual-key" | gcloud secrets create acme-hr-anthropic-key --data-file=-
```

- [ ] **Step 4: Create `deploy/deploy-backend.sh`**

```bash
#!/bin/bash
set -euo pipefail

PROJECT_ID=$(gcloud config get-value project)
REGION="us-central1"
IMAGE="gcr.io/$PROJECT_ID/acme-hr-backend:latest"
SERVICE_NAME="acme-hr-backend"

echo "Building and pushing image..."
cd "$(dirname "$0")/../backend"
docker build -t "$IMAGE" .
docker push "$IMAGE"

echo "Deploying to Cloud Run..."
gcloud run deploy "$SERVICE_NAME" \
  --image "$IMAGE" \
  --region "$REGION" \
  --platform managed \
  --allow-unauthenticated \
  --port 8080 \
  --memory 512Mi \
  --cpu 1 \
  --min-instances 0 \
  --max-instances 3 \
  --set-env-vars "DATABASE_URL=sqlite+aiosqlite:///./acme_hr.db" \
  --set-secrets "SECRET_KEY=acme-hr-secret-key:latest,ANTHROPIC_API_KEY=acme-hr-anthropic-key:latest" \
  --project "$PROJECT_ID"

echo "Getting service URL..."
gcloud run services describe "$SERVICE_NAME" --region "$REGION" --format "value(status.url)" --project "$PROJECT_ID"
```

- [ ] **Step 5: Make script executable and deploy**

```bash
chmod +x deploy/deploy-backend.sh

# Authenticate Docker with GCR
gcloud auth configure-docker

./deploy/deploy-backend.sh
```

Expected: Deployment succeeds. Script prints the Cloud Run service URL (e.g., `https://acme-hr-backend-xxxx-uc.a.run.app`).

- [ ] **Step 6: Verify the deployed backend**

```bash
SERVICE_URL=$(gcloud run services describe acme-hr-backend --region us-central1 --format "value(status.url)")
curl "$SERVICE_URL/health"
```

Expected: `{"status":"ok"}`

- [ ] **Step 7: Seed the production database**

```bash
# Cloud Run SQLite persists within a single instance but resets on scale-to-zero.
# For a demo/assessment, seed by invoking seed.py in the container:
gcloud run jobs create acme-hr-seed \
  --image "gcr.io/$(gcloud config get-value project)/acme-hr-backend:latest" \
  --region us-central1 \
  --command "python" \
  --args "seed.py" \
  --set-env-vars "DATABASE_URL=sqlite+aiosqlite:///./acme_hr.db" \
  --set-secrets "SECRET_KEY=acme-hr-secret-key:latest,ANTHROPIC_API_KEY=acme-hr-anthropic-key:latest"

gcloud run jobs execute acme-hr-seed --region us-central1 --wait
```

**Note:** SQLite on Cloud Run is suitable for a demo/assessment. For production, swap `DATABASE_URL` to a Cloud SQL PostgreSQL connection string.

- [ ] **Step 8: Commit**

```bash
git add deploy/deploy-backend.sh && git commit -m "feat: add Cloud Run deployment script for backend"
```

---

### Task 5: Firebase Hosting deployment (frontend)

**Files:**
- Create: `deploy/deploy-frontend.sh`
- Create: `frontend/firebase.json` (Firebase config)
- Create: `frontend/.firebaserc`

**Note:** You need the Firebase CLI (`npm install -g firebase-tools`) and to have run `firebase login` first.

- [ ] **Step 1: Initialize Firebase in the frontend directory**

```bash
cd frontend
firebase init hosting
```

When prompted:
- Project: select your GCP project
- Public directory: `dist`
- Single-page app: **Yes**
- GitHub Actions deploy: **No**

This generates `frontend/firebase.json` and `frontend/.firebaserc`.

- [ ] **Step 2: Update `frontend/firebase.json` to rewrite API calls to Cloud Run**

Replace the generated `frontend/firebase.json`:

```json
{
  "hosting": {
    "public": "dist",
    "ignore": ["firebase.json", "**/.*", "**/node_modules/**"],
    "rewrites": [
      {
        "source": "/auth/**",
        "run": {
          "serviceId": "acme-hr-backend",
          "region": "us-central1"
        }
      },
      {
        "source": "/api/**",
        "run": {
          "serviceId": "acme-hr-backend",
          "region": "us-central1"
        }
      },
      {
        "source": "**",
        "destination": "/index.html"
      }
    ]
  }
}
```

This routes `/auth/*` and `/api/*` to Cloud Run directly via Firebase Hosting rewrites (no separate nginx proxy needed in GCP).

- [ ] **Step 3: Update frontend Vite config for production (no proxy needed)**

Vite's proxy only runs in dev. The Firebase rewrites handle API routing in production. The frontend `lib/api.ts` already uses relative URLs (`baseURL: "/"`), which works in both dev (Vite proxy) and prod (Firebase rewrites).

- [ ] **Step 4: Create `deploy/deploy-frontend.sh`**

```bash
#!/bin/bash
set -euo pipefail

echo "Building frontend..."
cd "$(dirname "$0")/../frontend"
npm run build

echo "Deploying to Firebase Hosting..."
firebase deploy --only hosting

echo "Frontend deployed!"
firebase hosting:channel:list 2>/dev/null || true
```

- [ ] **Step 5: Deploy the frontend**

```bash
chmod +x deploy/deploy-frontend.sh
./deploy/deploy-frontend.sh
```

Expected: Firebase prints a hosting URL (e.g., `https://your-project.web.app`).

- [ ] **Step 6: Verify the deployed frontend**

Open the Firebase Hosting URL in a browser. Log in with `admin@acme.com / Admin123!`. All pages should work, with API calls routing to the Cloud Run backend.

- [ ] **Step 7: Commit**

```bash
git add deploy/deploy-frontend.sh frontend/firebase.json frontend/.firebaserc && git commit -m "feat: add Firebase Hosting deployment with Cloud Run rewrites"
```

---

### Task 6: Cloud Build CI/CD (optional)

**Files:**
- Create: `deploy/cloudbuild.yaml`

This automates deployment on every push to `main`. Skip if CI/CD is out of scope.

- [ ] **Step 1: Create `deploy/cloudbuild.yaml`**

```yaml
steps:
  # Test backend
  - name: 'python:3.12-slim'
    entrypoint: 'bash'
    args:
      - '-c'
      - |
        cd backend
        pip install -r requirements.txt -q
        pytest tests/ --tb=short -q

  # Build and push backend image
  - name: 'gcr.io/cloud-builders/docker'
    args: ['build', '-t', 'gcr.io/$PROJECT_ID/acme-hr-backend:$COMMIT_SHA', './backend']

  - name: 'gcr.io/cloud-builders/docker'
    args: ['push', 'gcr.io/$PROJECT_ID/acme-hr-backend:$COMMIT_SHA']

  # Deploy backend to Cloud Run
  - name: 'gcr.io/google.com/cloudsdktool/cloud-sdk'
    entrypoint: 'gcloud'
    args:
      - 'run'
      - 'deploy'
      - 'acme-hr-backend'
      - '--image=gcr.io/$PROJECT_ID/acme-hr-backend:$COMMIT_SHA'
      - '--region=us-central1'
      - '--platform=managed'
      - '--allow-unauthenticated'

  # Build and deploy frontend
  - name: 'node:20-alpine'
    entrypoint: 'sh'
    args:
      - '-c'
      - 'cd frontend && npm ci && npm run build'

  - name: 'gcr.io/google.com/cloudsdktool/cloud-sdk'
    entrypoint: 'bash'
    args:
      - '-c'
      - |
        npm install -g firebase-tools
        cd frontend
        firebase deploy --only hosting --token "$_FIREBASE_TOKEN"

substitutions:
  _FIREBASE_TOKEN: ''  # Set via Cloud Build trigger substitution variable

options:
  logging: CLOUD_LOGGING_ONLY
```

- [ ] **Step 2: Create a Cloud Build trigger (via GCP console)**

1. Go to GCP Console → Cloud Build → Triggers
2. Create trigger: connect your GitHub repo, branch=`main`, config file=`deploy/cloudbuild.yaml`
3. Add substitution variable `_FIREBASE_TOKEN` = output of `firebase login:ci`

- [ ] **Step 3: Commit**

```bash
git add deploy/cloudbuild.yaml && git commit -m "feat: add Cloud Build CI/CD pipeline for automated deployment"
```
