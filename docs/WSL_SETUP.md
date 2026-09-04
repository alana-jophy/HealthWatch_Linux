# HealthWatch — WSL Development Environment Guide

This guide describes how to run and develop HealthWatch on **Windows with WSL (Ubuntu 24.04.1 LTS)** and Docker.

---

## 1. Environment Path Reference

The project directory is accessible from both Windows and WSL:
- **Windows Path**: `C:\Users\Alana P J\.gemini\antigravity-ide\scratch\healthwatch`
- **WSL Path**: `/mnt/c/Users/Alana P J/.gemini/antigravity-ide/scratch/healthwatch`

---

## 2. Docker Execution in WSL

To start all services:
```bash
# Open WSL terminal
wsl -d Ubuntu-24.04

# Navigate to project root
cd "/mnt/c/Users/Alana P J/.gemini/antigravity-ide/scratch/healthwatch"

# Copy environment variables
cp .env.example .env

# Start services
docker compose up -d
```

### Checking Services Status:
```bash
docker compose ps
docker compose logs -f backend
```

---

## 3. Local Development (Without Docker)

### Backend (Python 3.11):
```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### Frontend (Node 20):
```bash
cd frontend
npm install
npm run dev
```

---

## 4. Port Allocations
- **Frontend Dashboard**: `http://localhost:5173`
- **Backend API**: `http://localhost:8000`
- **Interactive Swagger Docs**: `http://localhost:8000/docs`
- **Health Telemetry**: `http://localhost:8000/api/health`
- **PostGIS Database**: `localhost:5432`
