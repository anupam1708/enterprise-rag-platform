# CLAUDE.md - Enterprise RAG Platform

## Project Overview

Enterprise RAG (Retrieval-Augmented Generation) platform with a microservices architecture: Next.js frontend, Spring Boot API gateway, Python LangGraph AI agent, and PostgreSQL with pgvector.

## Repository Structure

```
frontend-nextjs/     # Next.js 14 (App Router) + TypeScript UI — port 3000
backend-java/        # Spring Boot 3.2 API gateway — port 8080
agent-python/        # Python FastAPI + LangGraph agent — port 8000
monitoring/          # Prometheus (9090) + Grafana (3001) config
.github/workflows/   # CI/CD pipelines
```

## Tech Stack

- **Frontend**: Next.js 14, React 18, TypeScript, Tailwind CSS, Recharts, Axios
- **Backend**: Java 17, Spring Boot 3.2.5, Spring AI, Spring Security + JWT, Resilience4j, Maven
- **Agent**: Python 3.11, FastAPI, LangChain 0.3, LangGraph 0.2, psycopg 3
- **Database**: PostgreSQL 16 + pgvector (embeddings dimension 1536)
- **Monitoring**: Prometheus, Grafana, LangSmith (optional)
- **Deployment**: Docker Compose, AWS EC2, Nginx

## Build & Run Commands

### Full stack (Docker Compose)
```bash
docker-compose up -d        # Start all 6 services
docker-compose down -v      # Stop and remove volumes
```

### Frontend
```bash
cd frontend-nextjs
npm install
npm run dev                 # Dev server on :3000
npm run build               # Production build
npm run lint                # ESLint + TS check
```

### Backend (Java)
```bash
cd backend-java
./mvnw spring-boot:run      # Dev server on :8081
./mvnw test                 # Run tests
./mvnw clean compile        # Compile only
./mvnw package -DskipTests  # Build JAR
```

### Python Agent
```bash
cd agent-python
pip install -r requirements.txt
uvicorn main:app --reload   # Dev server on :8000
```

### Python Linting
```bash
cd agent-python
flake8 . --count --select=E9,F63,F7,F82   # Errors only
flake8 . --max-complexity=10               # Warnings
```

### Python Tests
```bash
cd agent-python
python test_state_persistence.py   # State persistence tests
python test_hitl_workflow.py       # Human-in-the-loop tests
python evaluate_agent.py           # LangSmith evaluation (needs API key)
```

## Key Architecture Patterns

- **Hybrid RAG + Agent**: Documents exist → vector search via pgvector; no documents → LangGraph agent with web search fallback
- **Multi-Agent Supervisor**: Router dispatches to Research, Quantitative, and Writer agents
- **State Persistence**: PostgreSQL checkpointer with time-travel debugging (rewind to any checkpoint)
- **Generative UI**: SSE streams UI components (charts, tables, cards) instead of plain text
- **PII Redaction**: AOP-based aspect intercepts queries, regex-detects and masks sensitive data
- **Circuit Breaker**: Resilience4j protects backend from cascading failures (sliding window 10, threshold 50%)
- **Semantic Cache**: Query embeddings stored in PostgreSQL with IVFFlat index; similarity threshold 0.92
- **Human-in-the-Loop**: Interrupt agent execution for high-risk tool approval

## Database Schema (PostgreSQL + pgvector)

Key tables: `vector_store` (document embeddings), `users`, `chat_audit_logs`, `checkpoints` (LangGraph state), `checkpoint_writes`, `semantic_cache`

Initialization scripts: `init-db.sql` (DB + pgvector extension), `init-tables.sql` (schema)

## Configuration

- `backend-java/src/main/resources/application.properties.example` — Spring Boot config
- `agent-python/.env.example` — Python agent env vars
- `monitoring/prometheus.yml` — Prometheus scrape targets
- `monitoring/alerts.yml` — Alert rules (ServiceDown, HighErrorRate, etc.)

## CI/CD

- `.github/workflows/ci.yml` — Build, test, lint, security scan (Trivy), LangSmith eval (main only)
- `.github/workflows/deploy-aws.yml` — EC2 deployment via SCP + SSH
- `.github/workflows/docker-build.yml` — Docker image builds
- `.github/workflows/red-team-security.yml` — Security red team tests

## Code Style Notes

- Frontend uses Next.js App Router conventions (`app/` directory)
- Backend follows Spring Boot layered architecture (controller → service → repository)
- Python agent uses FastAPI with Pydantic models
- All Dockerfiles use multi-stage builds for minimal image size
