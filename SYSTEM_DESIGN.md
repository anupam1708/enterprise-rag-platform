# Enterprise RAG Platform — System Design Document

**Version:** 1.0  
**Date:** 2026-04-15  
**Author:** Engineering Team  

---

## Table of Contents

1. [Overview](#1-overview)
2. [Architecture Diagram](#2-architecture-diagram)
3. [Layer-by-Layer Design](#3-layer-by-layer-design)
   - 3.1 [Presentation Layer — Next.js Frontend](#31-presentation-layer--nextjs-frontend)
   - 3.2 [API Gateway Layer — Java Spring Boot](#32-api-gateway-layer--java-spring-boot)
   - 3.3 [Agent & Orchestration Layer — Python / LangGraph](#33-agent--orchestration-layer--python--langgraph)
   - 3.4 [Data Layer — PostgreSQL + pgvector](#34-data-layer--postgresql--pgvector)
   - 3.5 [AI / ML Layer](#35-ai--ml-layer)
   - 3.6 [Search Integration Layer](#36-search-integration-layer)
   - 3.7 [Observability Layer](#37-observability-layer)
   - 3.8 [Infrastructure & Deployment Layer](#38-infrastructure--deployment-layer)
4. [Cross-Cutting Concerns](#4-cross-cutting-concerns)
   - 4.1 [Authentication & Authorization](#41-authentication--authorization)
   - 4.2 [PII Sanitization](#42-pii-sanitization)
   - 4.3 [Semantic Caching](#43-semantic-caching)
   - 4.4 [Human-in-the-Loop (HITL)](#44-human-in-the-loop-hitl)
   - 4.5 [Fault Tolerance](#45-fault-tolerance)
5. [Key Data Flows](#5-key-data-flows)
   - 5.1 [Document Ingestion Flow](#51-document-ingestion-flow)
   - 5.2 [Standard RAG Chat Flow](#52-standard-rag-chat-flow)
   - 5.3 [Stateful Agent Flow](#53-stateful-agent-flow)
   - 5.4 [Multi-Agent Supervisor Flow](#54-multi-agent-supervisor-flow)
   - 5.5 [HITL Approval Flow](#55-hitl-approval-flow)
   - 5.6 [Generative UI Streaming Flow](#56-generative-ui-streaming-flow)
6. [Database Schema](#6-database-schema)
7. [API Reference](#7-api-reference)
8. [Architectural Patterns & Decisions](#8-architectural-patterns--decisions)
9. [Security Model](#9-security-model)
10. [Scalability & Performance](#10-scalability--performance)
11. [Configuration Reference](#11-configuration-reference)

---

## 1. Overview

The Enterprise RAG Platform is a production-grade, compliance-focused Retrieval-Augmented Generation system. It enables organizations to ingest proprietary documents and query them via natural language, with full auditability, PII protection, and human oversight on high-risk AI actions.

### Core Capabilities

| Capability | Description |
|---|---|
| **Document RAG** | Upload PDFs; query them with semantic search + LLM generation |
| **Stateful Agents** | Multi-turn conversations persisted to PostgreSQL; time-travel debugging |
| **Multi-Agent Supervisor** | Specialized Research, Quantitative, and Writer sub-agents |
| **Human-in-the-Loop** | Interrupt graph before high-risk tool calls; require human approval |
| **Generative UI** | Stream rich chart/card UI artifacts alongside text responses |
| **Hybrid Search** | Route queries to Tavily (recency) or Exa (depth) automatically |
| **Semantic Caching** | Return vector-similar cached answers to reduce LLM latency and cost |
| **PII Sanitization** | Strip PII from all user input before storage via AOP |
| **Compliance Audit Log** | Record every query, response, and PII event |
| **Observability** | Prometheus metrics + Grafana dashboards + LangSmith tracing |

### Technology Stack Summary

| Layer | Technology |
|---|---|
| Frontend | Next.js 14, React 18, Tailwind CSS, Recharts, TypeScript |
| API Gateway | Spring Boot 3.2, Java 17, Spring AI 1.0, Resilience4j |
| Agent Engine | FastAPI, Python 3.11, LangGraph 0.2, LangChain 0.3 |
| Database | PostgreSQL 16 + pgvector extension |
| LLM | OpenAI GPT-4o-mini (agents), GPT-4-turbo (RAG), text-embedding-3-small |
| Search | Tavily (news), Exa (research) |
| Monitoring | Prometheus, Grafana, LangSmith, AWS CloudWatch |
| Infrastructure | Docker Compose, AWS EC2, GitHub Actions CI/CD |

---

## 2. Architecture Diagram

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                          PRESENTATION LAYER                                   │
│  ┌─────────────────────────────────────────────────────────────────────────┐ │
│  │                    Next.js 14 Frontend (Port 3000)                       │ │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌─────────────┐ │ │
│  │  │  ChatInterface│  │  HITLChat    │  │DocumentUpload│  │  Auth Pages │ │ │
│  │  │  (SSE stream) │  │ (Approvals)  │  │  (PDF ingest)│  │ login/reg   │ │ │
│  │  └──────────────┘  └──────────────┘  └──────────────┘  └─────────────┘ │ │
│  │  ┌──────────────────────────────────────────────────────────────────────┐ │ │
│  │  │         ArtifactComponents (LineChart, BarChart, DataTable, Cards)   │ │ │
│  │  └──────────────────────────────────────────────────────────────────────┘ │ │
│  │                    AuthContext (JWT, localStorage)                         │ │
│  └─────────────────────────────────────────────────────────────────────────┘ │
└──────────────────────────────┬───────────────────────────────────────────────┘
                               │ HTTPS / REST + SSE
┌──────────────────────────────▼───────────────────────────────────────────────┐
│                        API GATEWAY LAYER                                      │
│  ┌─────────────────────────────────────────────────────────────────────────┐ │
│  │              Java Spring Boot Backend (Port 8080)                        │ │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────────────┐  │ │
│  │  │ChatController │  │AuthController│  │    IngestionController       │  │ │
│  │  │ GET /api/chat │  │ POST /login  │  │    POST /api/ingest          │  │ │
│  │  │ GET /api/chat │  │ POST /register│  │    (PDF → embeddings)       │  │ │
│  │  │       /agent  │  └──────────────┘  └──────────────────────────────┘  │ │
│  │  └──────┬───────┘                                                        │ │
│  │         │                                                                 │ │
│  │  ┌──────▼──────────────────────────────────────────────────────────────┐ │ │
│  │  │                      Service Layer                                   │ │ │
│  │  │  ┌────────────┐  ┌──────────────┐  ┌────────────┐  ┌─────────────┐ │ │ │
│  │  │  │ChatService │  │IngestionSvc  │  │AuthSvc     │  │DataGuardSvc │ │ │ │
│  │  │  │(RAG pipeline│  │(PDF chunking │  │(JWT gen/val│  │(PII detect) │ │ │ │
│  │  │  │+ audit log) │  │ + embedding) │  │)           │  │             │ │ │ │
│  │  │  └─────┬──────┘  └──────┬───────┘  └────────────┘  └─────────────┘ │ │ │
│  │  └────────┼────────────────┼─────────────────────────────────────────-─┘ │ │
│  │           │                │     ┌─────────────────────────────────────┐  │ │
│  │           │                │     │ PiiSanitizationAspect (AOP)         │  │ │
│  │           │                │     │ @SanitizePii annotation intercept   │  │ │
│  │           │                │     └─────────────────────────────────────┘  │ │
│  │           │                │     ┌─────────────────────────────────────┐  │ │
│  │           │                │     │ JwtAuthenticationFilter             │  │ │
│  │           │                │     │ SecurityConfig (stateless sessions)  │  │ │
│  │           │                │     └─────────────────────────────────────┘  │ │
│  │           │ Circuit Breaker│ Spring AI Embeddings                         │ │
│  │     ┌─────▼──────┐  ┌──────▼──────────────────────────┐                 │ │
│  │     │PythonAgent │  │   pgvector Vector Store          │                 │ │
│  │     │Client      │  │   (Spring AI integration)        │                 │ │
│  │     │(Resilience4│  │   HNSW index, 1536-dim vectors   │                 │ │
│  │     │j fallback) │  └──────────────────────────────────┘                 │ │
│  │     └─────┬──────┘                                                       │ │
│  └───────────┼──────────────────────────────────────────────────────────────┘ │
└─────────────-┼────────────────────────────────────────────────────────────────┘
               │ HTTP REST
┌──────────────▼───────────────────────────────────────────────────────────────┐
│                   AGENT & ORCHESTRATION LAYER                                 │
│  ┌─────────────────────────────────────────────────────────────────────────┐ │
│  │              Python FastAPI Agent Service (Port 8000)                    │ │
│  │                                                                           │ │
│  │  Endpoints:                                                               │ │
│  │  POST /api/graph        → Stateful LangGraph agent (with HITL)           │ │
│  │  POST /api/graph/approve → Human approval/rejection                      │ │
│  │  POST /api/multi-agent  → Multi-agent supervisor (with semantic cache)   │ │
│  │  GET  /api/history/{id} → Conversation history                           │ │
│  │  POST /api/rewind       → Time-travel to past checkpoint                 │ │
│  │                                                                           │ │
│  │  ┌─────────────────────────────────────────────────────────────────────┐ │ │
│  │  │                  LangGraph StateGraph                                │ │ │
│  │  │                                                                      │ │ │
│  │  │   ┌──────────┐   tool_call?  ┌──────────────┐                      │ │ │
│  │  │   │call_model│──────────────▶│  call_tool   │                      │ │ │
│  │  │   │ (GPT-4o  │◀─────────────│ (ToolExecutor│                      │ │ │
│  │  │   │  -mini)  │  ToolMessage  │  + HITL check│                      │ │ │
│  │  │   └──────────┘               └──────────────┘                      │ │ │
│  │  │         │ no more tool calls                                         │ │ │
│  │  │         ▼                                                            │ │ │
│  │  │       END                                                            │ │ │
│  │  │                                                                      │ │ │
│  │  │   State: AgentState { messages: List[BaseMessage] }                 │ │ │
│  │  │   Persistence: PostgresSaver (checkpoint per node execution)        │ │ │
│  │  └─────────────────────────────────────────────────────────────────────┘ │ │
│  │                                                                           │ │
│  │  ┌─────────────────────────────────────────────────────────────────────┐ │ │
│  │  │              Multi-Agent Supervisor                                  │ │ │
│  │  │                                                                      │ │ │
│  │  │        ┌───────────────────────────────┐                            │ │ │
│  │  │        │         Supervisor LLM         │                           │ │ │
│  │  │        │   (routes to sub-agents)       │                           │ │ │
│  │  │        └──┬─────────────┬──────────────┘                           │ │ │
│  │  │           │             │              │                             │ │ │
│  │  │    ┌──────▼───┐  ┌─────▼──────┐  ┌───▼─────┐                     │ │ │
│  │  │    │ Research │  │Quantitative│  │  Writer │                      │ │ │
│  │  │    │  Agent   │  │   Agent    │  │  Agent  │                      │ │ │
│  │  │    │(web,scrape│  │(yfinance, │  │(format, │                      │ │ │
│  │  │    │  hybrid) │  │  pandas)   │  │ summary)│                      │ │ │
│  │  │    └──────────┘  └────────────┘  └─────────┘                     │ │ │
│  │  └─────────────────────────────────────────────────────────────────────┘ │ │
│  │                                                                           │ │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐                  │ │
│  │  │ hybrid_search│  │semantic_cache│  │generative_ui │                  │ │
│  │  │(Tavily | Exa)│  │(pgvector cos)│  │(SSE artifacts│                  │ │
│  │  └──────────────┘  └──────────────┘  └──────────────┘                  │ │
│  └─────────────────────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────────────────┘
                               │ SQL + pgvector queries
┌──────────────────────────────▼───────────────────────────────────────────────┐
│                            DATA LAYER                                         │
│  ┌─────────────────────────────────────────────────────────────────────────┐ │
│  │                   PostgreSQL 16 + pgvector (Port 5432)                   │ │
│  │                        Database: compliance_db                            │ │
│  │                                                                           │ │
│  │  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌────────────────┐ │ │
│  │  │ vector_store  │ │    users     │ │chat_audit_log│ │  checkpoints   │ │ │
│  │  │(HNSW, 1536d) │ │(JWT auth)    │ │(compliance)  │ │(LangGraph state│ │ │
│  │  └──────────────┘ └──────────────┘ └──────────────┘ └────────────────┘ │ │
│  │  ┌──────────────┐ ┌──────────────┐                                      │ │
│  │  │semantic_cache │ │checkpoint_   │                                      │ │
│  │  │(IVFFlat,1536d│ │  writes      │                                      │ │
│  │  └──────────────┘ └──────────────┘                                      │ │
│  └─────────────────────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────────────────┘
                               │
┌──────────────────────────────▼───────────────────────────────────────────────┐
│                        OBSERVABILITY LAYER                                    │
│   Prometheus (9090)  ──▶  Grafana (3001)                                     │
│   LangSmith  ──────────▶  (agent traces)                                     │
│   AWS CloudWatch  ──────▶  (container logs)                                  │
└──────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Layer-by-Layer Design

### 3.1 Presentation Layer — Next.js Frontend

**Directory:** [frontend-nextjs/](frontend-nextjs/)  
**Port:** 3000

#### Technology Choices
- **Next.js 14** with App Router for file-based routing and server components
- **React 18** for concurrent rendering and streaming UI
- **Tailwind CSS** for utility-first styling
- **Recharts** for rendering data visualizations received as JSON artifacts
- **Axios** for REST calls; native `EventSource` for SSE streaming
- **TypeScript** for compile-time safety

#### Page Structure

| Route | File | Purpose |
|---|---|---|
| `/` | [app/page.tsx](frontend-nextjs/app/page.tsx) | Main dashboard; tab-based nav (Chat, HITL, Upload) |
| `/login` | [app/login/page.tsx](frontend-nextjs/app/login/page.tsx) | User sign-in |
| `/register` | [app/register/page.tsx](frontend-nextjs/app/register/page.tsx) | User registration |

#### Key Components

**[ChatInterface.tsx](frontend-nextjs/components/ChatInterface.tsx)**
- Sends queries to Java backend (`/api/chat`) or Python agent (`/python-api/api/graph`)
- Opens an `EventSource` connection for SSE streaming from Python generative UI endpoint
- Parses incoming JSON lines as `UIArtifact` objects and hands them to `ArtifactComponents`
- Maintains a local message array in `useState`; no external state manager needed

**[HITLChat.tsx](frontend-nextjs/components/HITLChat.tsx)**
- Polls Python agent for `pending_approval` status after agent response
- Renders an approval card showing tool name, inputs, and risk level
- `POST /api/graph/approve` with `{ approve: true/false }` to resume or abort graph execution
- Shows post-decision badge (Approved / Rejected) for audit trail

**[DocumentUpload.tsx](frontend-nextjs/components/DocumentUpload.tsx)**
- Multipart form POST to Java backend `/api/ingest`
- Shows upload progress and success/error state

**[artifacts/ArtifactComponents.tsx](frontend-nextjs/components/artifacts/ArtifactComponents.tsx)**
- Maps artifact type enum to React component:
  - `LINE_CHART`, `BAR_CHART`, `AREA_CHART`, `PIE_CHART` → Recharts wrappers
  - `DATA_TABLE` → sortable HTML table
  - `STOCK_CARD`, `COMPARISON_CARD`, `METRIC_CARD` → styled cards

#### State Management

**[contexts/AuthContext.tsx](frontend-nextjs/contexts/AuthContext.tsx)**
- Stores JWT token and decoded user payload (username, email, role) in `localStorage`
- Provides `login()`, `register()`, `logout()` methods across the app via React Context
- `ProtectedRoute` wrapper redirects unauthenticated users to `/login`

#### API Routing
- Java backend: `NEXT_PUBLIC_API_URL` (default `http://localhost:8080`)
- Python agent: proxied through nginx path `/python-api` to avoid CORS and mixed content

---

### 3.2 API Gateway Layer — Java Spring Boot

**Directory:** [backend-java/](backend-java/)  
**Port:** 8080  
**Build:** Maven multi-stage Docker image on eclipse-temurin:17-jre

#### Responsibilities
1. Authenticate requests (JWT filter)
2. Sanitize PII from user input (AOP aspect)
3. Execute the standard RAG pipeline against pgvector
4. Proxy advanced agent requests to the Python microservice with circuit breaker
5. Handle document ingestion (PDF parse → chunk → embed → store)
6. Write compliance audit logs

#### Controller → Service → Repository Flow

```
HTTP Request
    │
    ▼
JwtAuthenticationFilter         (validates Bearer token, sets SecurityContext)
    │
    ▼
PiiSanitizationAspect           (strips PII from annotated method args)
    │
    ├─▶ ChatController  ──────▶ ChatService ──────▶ PgvectorVectorStore
    │      /api/chat                │                    (top-3 similarity)
    │      /api/chat/agent          │               PythonAgentClient
    │                               │                    (circuit breaker)
    │                               └──────▶ ChatAuditRepository
    │
    ├─▶ AuthenticationController ▶ AuthenticationService ▶ UserRepository
    │      /api/auth/login                   JwtService
    │      /api/auth/register
    │
    └─▶ IngestionController ─────▶ IngestionService ──▶ PDFBox (extract)
           /api/ingest                                    TokenTextSplitter (chunk)
                                                          PgvectorVectorStore (embed + store)
```

#### Core Services

**ChatService**
1. Receives sanitized query
2. Searches pgvector for top-3 similar document chunks
3. If documents found: builds context-enriched prompt → Spring AI `ChatClient` → GPT-4-turbo
4. If no documents: falls back to `PythonAgentClient`
5. Writes `ChatAuditLog` record (user, query, sanitized_query, response, pii_detected)

**IngestionService**
1. PDFBox extracts raw text from uploaded file
2. `TokenTextSplitter` chunks text (800 tokens, 400-token overlap)
3. Spring AI generates OpenAI embeddings for each chunk
4. Stores chunks + vectors into `vector_store` table via pgvector Spring AI integration

**PythonAgentClient**
- Calls `http://python-agent:8000/api/graph` with query payload
- Wrapped in Resilience4j `CircuitBreaker`: failure threshold 50%, sliding window 10 requests
- Fallback method returns user-friendly degradation message

**DataGuardService**
- PII pattern matching (email, SSN, credit card regex)
- Sanitizes strings before they reach database layer

#### Security

- `JwtService`: HS256 signing, 24-hour expiry, claims: username, email, role
- `JwtAuthenticationFilter`: stateless per-request validation; no session state
- `SecurityConfig`: permits `/api/auth/**` and `/actuator/**` publicly; requires JWT for all else; CSRF disabled; CORS permissive in dev
- `@SanitizePii` + `PiiSanitizationAspect`: AOP intercepts annotated methods, redacts PII before execution continues

#### Configuration

| Property | Value |
|---|---|
| Port | 8080 |
| OpenAI model | gpt-4-turbo |
| Temperature | 0.3 |
| pgvector dimensions | 1536 |
| pgvector index | HNSW (cosine) |
| JWT expiry | 24 hours |
| Max upload size | 10 MB |

---

### 3.3 Agent & Orchestration Layer — Python / LangGraph

**Directory:** [agent-python/](agent-python/)  
**Port:** 8000  
**Runtime:** Python 3.11, FastAPI + Uvicorn

#### Responsibilities
1. Serve stateful multi-turn conversations via LangGraph `StateGraph`
2. Execute tool calls (web search, stock data, file operations)
3. Interrupt before high-risk tools and await human approval (HITL)
4. Route complex queries to specialized sub-agents via supervisor
5. Cache semantically similar queries in pgvector
6. Stream generative UI artifacts (charts, cards, tables) over SSE

#### Module Map

| File | Size | Role |
|---|---|---|
| [main.py](agent-python/main.py) | 27 KB | FastAPI app, all HTTP endpoints, lifecycle management |
| [graph_agent.py](agent-python/graph_agent.py) | 19 KB | LangGraph StateGraph, HITL tool gating, PostgresSaver |
| [multi_agent_supervisor.py](agent-python/multi_agent_supervisor.py) | 23 KB | Supervisor pattern, Research/Quant/Writer agents |
| [semantic_cache.py](agent-python/semantic_cache.py) | 8.5 KB | pgvector cosine cache with TTL |
| [hybrid_search.py](agent-python/hybrid_search.py) | 5.5 KB | Tavily/Exa router |
| [generative_ui.py](agent-python/generative_ui.py) | 20.5 KB | Artifact builder, yfinance data, SSE streamer |
| [agent.py](agent-python/agent.py) | — | Simple tool-calling agent (basic queries) |

#### LangGraph StateGraph Design

```
                    ┌─────────────────┐
START ──────────────▶   call_model    │
                    │  (GPT-4o-mini)  │
                    │  binds tools    │
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │ tool_call in    │
                    │ response?       │
                    └──┬──────────┬───┘
                    Yes│          │No
                       │          └──────────────▶ END
              ┌────────▼────────┐
              │  HITL_TOOLS     │
              │  check          │
              └──┬──────────┬───┘
           Safe │          │ High-risk
                │          │ (buy_stock,
                │          │  send_email,
                │          │  delete_db_records)
                │          ▼
                │   ┌──────────────┐
                │   │ INTERRUPT    │
                │   │ (await human │
                │   │  approval)   │
                │   └──────┬───────┘
                │    Approve│Reject
                │   ┌───────▼───────┐
                │   │ Resume or     │
                │   │ skip tool     │
                │   └───────────────┘
                ▼
        ┌───────────────┐
        │  call_tool    │
        │ (ToolExecutor)│
        └───────┬───────┘
                │ ToolMessage
                └──────────────────────▶ call_model (loop)
```

**State:** `AgentState = { messages: List[BaseMessage] }`  
**Persistence:** `PostgresSaver` writes a checkpoint JSON blob to `checkpoints` table after each node; enables rewind via `POST /api/rewind`  
**Multi-tenancy:** Every conversation identified by `thread_id`; graph config sets `configurable: { thread_id }`

#### Multi-Agent Supervisor Design

```
Query ──▶ POST /api/multi-agent
               │
               ▼
    ┌──────────────────────┐
    │    Semantic Cache     │ ──── HIT ──▶ return cached response
    │    (pgvector, 0.92)   │
    └──────────┬───────────┘
               │ MISS
               ▼
    ┌──────────────────────┐
    │   Supervisor Node     │
    │   (GPT-4o-mini)       │
    │   Decides: which      │
    │   agents needed?      │
    └──┬──────────┬─────┬───┘
       │          │     │
       ▼          ▼     ▼
   Research   Quant   Writer
   Agent      Agent   Agent
   (Tavily/   (yfinance (format
    Exa,       pandas)  results)
    scrape)
       │          │     │
       └──────────┴─────┘
               │ merged results
               ▼
    ┌──────────────────────┐
    │  Semantic Cache PUT   │
    └──────────────────────┘
               │
               ▼
           Response
```

#### HITL Tool Classification

| Tool | Risk Level | Approval Required |
|---|---|---|
| `hybrid_web_search` | Safe | No |
| `get_stock_price` | Safe | No |
| `scrape_summary` | Safe | No |
| `buy_stock` | High | Yes |
| `send_email` | High | Yes |
| `delete_database_records` | Critical | Yes |

---

### 3.4 Data Layer — PostgreSQL + pgvector

**Image:** `pgvector/pgvector:pg16`  
**Port:** 5432  
**Database:** `compliance_db`

#### Tables Overview

| Table | Owner Service | Primary Purpose |
|---|---|---|
| `vector_store` | Java backend | Stores document chunk embeddings for RAG retrieval |
| `users` | Java backend | User accounts (JWT auth) |
| `chat_audit_logs` | Java backend | Full audit trail of every query+response |
| `checkpoints` | Python agent | LangGraph state snapshots (full conversation graph) |
| `checkpoint_writes` | Python agent | In-flight node write buffers |
| `semantic_cache` | Python agent | Cached (query_embedding → response) pairs with TTL |

#### Vector Indexing Strategy

| Table | Index Type | Reason |
|---|---|---|
| `vector_store` | HNSW (cosine) | High-recall approximate search; best for RAG top-k retrieval |
| `semantic_cache` | IVFFlat (cosine) | Faster index build; cache lookup is latency-critical |

Both indexes operate on 1536-dimensional float vectors produced by OpenAI `text-embedding-3-small`.

#### Schema Details

**vector_store**
```sql
id         UUID PRIMARY KEY DEFAULT gen_random_uuid()
content    TEXT NOT NULL
embedding  vector(1536)
metadata   JSONB
```

**users**
```sql
id           BIGSERIAL PRIMARY KEY
username     VARCHAR(50) UNIQUE NOT NULL
email        VARCHAR(100) UNIQUE NOT NULL
password     TEXT NOT NULL          -- BCrypt hashed
role         VARCHAR(20) NOT NULL   -- USER | ADMIN
created_at   TIMESTAMP DEFAULT NOW()
enabled      BOOLEAN DEFAULT TRUE
```

**chat_audit_logs**
```sql
id               BIGSERIAL PRIMARY KEY
user_id          BIGINT REFERENCES users(id)
user_query       TEXT
sanitized_query  TEXT
ai_response      TEXT
timestamp        TIMESTAMP DEFAULT NOW()
pii_detected     BOOLEAN DEFAULT FALSE
```

**checkpoints** (LangGraph-managed)
```sql
thread_id       TEXT NOT NULL
checkpoint_id   TEXT NOT NULL
checkpoint      JSONB NOT NULL
metadata        JSONB
```

**semantic_cache**
```sql
query_hash      TEXT PRIMARY KEY
query_text      TEXT NOT NULL
query_embedding vector(1536) NOT NULL
response_text   TEXT NOT NULL
created_at      TIMESTAMP DEFAULT NOW()
expires_at      TIMESTAMP NOT NULL
hit_count       INTEGER DEFAULT 0
```

---

### 3.5 AI / ML Layer

#### LLM Configuration

| Service | Model | Temperature | Use |
|---|---|---|---|
| Java RAG pipeline | gpt-4-turbo | 0.3 | Deterministic compliance responses |
| Python graph agent | gpt-4o-mini | 0.0 | Tool-calling, structured output |
| Python multi-agent | gpt-4o-mini | varies | Research, quant, writing tasks |

#### Embedding Model
- **Model:** `text-embedding-3-small`
- **Dimensions:** 1536
- **Used for:** Document chunks (ingestion), query embedding (retrieval), semantic cache lookup

#### RAG Pipeline (Java)

```
1. INGEST
   PDF file ──▶ PDFBox.extractText()
             ──▶ TokenTextSplitter(size=800, overlap=400)
             ──▶ OpenAI embeddings (text-embedding-3-small)
             ──▶ pgvector INSERT (content, embedding, metadata)

2. RETRIEVE
   User query ──▶ OpenAI embeddings
              ──▶ pgvector cosine similarity search (top-3)
              ──▶ Context chunks returned

3. GENERATE
   System prompt + context + user query
              ──▶ Spring AI ChatClient
              ──▶ GPT-4-turbo (temp=0.3)
              ──▶ Response
```

#### Agent Tool Execution (Python)

```
1. Model sees user message
2. Model decides to call tool → emits ToolCall in response
3. ToolExecutor invokes Python function (may call Tavily/Exa/yfinance)
4. Returns ToolMessage with result
5. Loop: model sees ToolMessage, decides next action
6. Terminates when model emits text-only response (no ToolCall)
```

---

### 3.6 Search Integration Layer

**Module:** [agent-python/hybrid_search.py](agent-python/hybrid_search.py)

#### Routing Algorithm (Pattern-Based, Zero LLM Tokens)

```python
RECENT_SIGNALS = ["latest", "news", "current", "price", "today", "breaking"]
DEEP_SIGNALS   = ["explain", "research", "academic", "architecture", "paper"]

if any(s in query.lower() for s in RECENT_SIGNALS):
    primary = Tavily
elif any(s in query.lower() for s in DEEP_SIGNALS):
    primary = Exa
else:
    primary = Tavily  # default
```

#### Provider Comparison

| Attribute | Tavily | Exa |
|---|---|---|
| Best for | Breaking news, real-time prices, trending | Academic papers, technical docs, deep research |
| Search depth | "advanced" | Semantic / autoprompt |
| Time range | "month" (configurable) | Not time-bounded |
| Highlights | Snippets | 3 sentences per URL |
| Fallback | Exa | Tavily |

---

### 3.7 Observability Layer

**Directory:** [monitoring/](monitoring/)

#### Metrics (Prometheus + Grafana)

| Component | Metrics Exposed | Endpoint |
|---|---|---|
| Java backend | JVM heap, HTTP latency, request count, error rate, cache hits | `/actuator/prometheus` |
| Prometheus | Self-monitoring | Port 9090 |
| Grafana | Dashboards | Port 3001 |

Key alert rules ([monitoring/alerts.yml](monitoring/alerts.yml)):
- High CPU / memory utilization thresholds
- HTTP 5xx spike detection
- JVM GC pause time

#### Distributed Tracing (LangSmith)
- `LANGCHAIN_TRACING_V2=true` in Python agent environment
- Every agent invocation creates a trace in LangSmith project `agent-python`
- Visualizes: node execution order, tool calls, token counts, latencies

#### Application Logs (AWS CloudWatch)
- Log driver: `awslogs`
- Log group: `/ecs/compliance-rag`
- Stream per service: `python-agent`, `java-backend`
- Region: `us-east-2`

---

### 3.8 Infrastructure & Deployment Layer

**Orchestration:** [docker-compose.yml](docker-compose.yml)

#### Service Topology

```
                        ┌─────────────────┐
                        │    Frontend      │
                        │  Next.js :3000   │
                        └────────┬─────────┘
                                 │
                        ┌────────▼─────────┐
                        │  Java Backend    │
                        │  Spring Boot     │
                        │    :8080         │
                        └──┬──────────┬────┘
                           │          │
              ┌────────────▼──┐   ┌───▼──────────────┐
              │ Python Agent  │   │    PostgreSQL 16  │
              │  FastAPI      │   │  + pgvector :5432 │
              │   :8000       │   └───────────────────┘
              └───────────────┘
                           │
              ┌────────────▼──┐   ┌───────────────────┐
              │  Prometheus   │   │     Grafana         │
              │    :9090      │──▶│      :3001          │
              └───────────────┘   └───────────────────-┘
```

#### Volume Mounts
- `postgres_data` — persistent DB storage survives container restarts
- `prometheus_data` — metric history
- `grafana_data` — dashboard state

#### CI/CD Pipelines ([.github/workflows/](.github/workflows/))

| Workflow | Trigger | Jobs |
|---|---|---|
| `ci.yml` | Push to `main`/`develop`, PR | Maven test + package; npm install + test |
| `deploy-aws.yml` | Push to `main` (or manual) | Package all services → SCP to EC2 → SSH docker-compose up |
| `red-team-security.yml` | Scheduled / PR | Run `red_team/run_red_team_tests.py`; fail on critical vulnerabilities |
| `docker-build.yml` | Push | Build + push Docker images to registry |

#### AWS Deployment
- Target: EC2 instance (`EC2_HOST` secret)
- Deployment: SSH + `docker-compose up -d` with `deployment.tar.gz`
- Secrets: `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `EC2_HOST`, `EC2_USER`, `EC2_SSH_KEY`

---

## 4. Cross-Cutting Concerns

### 4.1 Authentication & Authorization

```
User                 Frontend              Java Backend
 │                       │                      │
 │── POST /api/auth/login ──────────────────────▶│
 │                       │          AuthSvc.login│
 │                       │          BCrypt verify │
 │                       │          JwtService   │
 │◀── JWT (24h) ──────────────────────────────────│
 │                       │                      │
 │── GET /api/chat ────── Authorization: Bearer <token> ──▶│
 │                       │          JwtAuthFilter.doFilter│
 │                       │          JwtService.validateToken│
 │                       │          SecurityContext.setAuth│
 │                       │          ChatController ──────▶│
```

**JWT Payload:** `{ sub: username, email, role, iat, exp }`  
**Secret:** HS256 HMAC key (configured via environment variable)  
**Expiry:** 86400 seconds (24 hours)

### 4.2 PII Sanitization

Spring AOP intercepts methods annotated with `@SanitizePii`:

```
Method Call
    │
    ▼
PiiSanitizationAspect.before()
    │
    ├── Scan all String args for PII patterns:
    │   ├── Email regex
    │   ├── SSN pattern (\d{3}-\d{2}-\d{4})
    │   └── Credit card pattern (16-digit groups)
    │
    ├── Replace matches with [REDACTED]
    ├── Set pii_detected = true on audit log
    │
    └── Proceed with sanitized args
```

Applied to: `ChatService.chat()`, all `ChatController` endpoints

### 4.3 Semantic Caching

**Flow:**
```
POST /api/multi-agent
    │
    ▼
SemanticCache.get(query)
    ├── Embed query via text-embedding-3-small
    ├── SQL: SELECT response_text, similarity
    │         FROM semantic_cache
    │         WHERE expires_at > NOW()
    │         ORDER BY embedding <=> query_embedding
    │         LIMIT 1
    │
    ├── similarity >= 0.92? ──▶ HIT: return cached response
    │                              (latency: <10ms vs ~2000ms LLM)
    └── MISS: invoke LLM pipeline
              │
              └──▶ SemanticCache.put(query, response)
                   (TTL: 300 seconds)
```

**Cost model:** Each cache hit saves approximately $0.03 in LLM API costs.

### 4.4 Human-in-the-Loop (HITL)

```
Agent calls high-risk tool (e.g., buy_stock)
    │
    ▼
LangGraph INTERRUPT before tool node
State saved to PostgreSQL checkpoint
    │
    ▼
POST /api/graph returns { pending_approval: true, tool_name, tool_inputs }
    │
    ▼
Frontend renders approval card
User clicks Approve or Reject
    │
    ▼
POST /api/graph/approve { thread_id, approve: true/false }
    │
    ├── approve=true  ──▶ Resume graph from saved checkpoint
    └── approve=false ──▶ Inject rejection ToolMessage, continue to END
```

### 4.5 Fault Tolerance

**Resilience4j Circuit Breaker** (Java → Python):

| Parameter | Value |
|---|---|
| Failure rate threshold | 50% |
| Sliding window size | 10 requests |
| Wait duration in OPEN state | 5 seconds |
| Fallback | "⚠️ Advanced Agent offline. Please try standard RAG instead." |

**Hybrid Search Fallback** (Python):  
If primary search engine (Tavily or Exa) returns an error → automatically retry with the other engine.

---

## 5. Key Data Flows

### 5.1 Document Ingestion Flow

```
User                   Frontend           Java Backend          PostgreSQL
 │                         │                    │                    │
 │─ Select PDF ────────────▶│                    │                    │
 │                         │── POST /api/ingest ▶│                    │
 │                         │   multipart/form   │                    │
 │                         │                    │── PDFBox.extract() │
 │                         │                    │── TokenTextSplitter│
 │                         │                    │   (800 tok chunks) │
 │                         │                    │── OpenAI Embed ───▶│(HTTP)
 │                         │                    │◀── embeddings ─────│
 │                         │                    │── INSERT vector_store▶│
 │                         │◀── 200 OK ──────── │                    │
 │◀─ "Upload successful" ──│                    │                    │
```

### 5.2 Standard RAG Chat Flow

```
User          Frontend         Java Backend      pgvector       OpenAI
 │                │                 │                │              │
 │─ Send query ──▶│                 │                │              │
 │                │── GET /api/chat ▶│               │              │
 │                │                 │── embed query ────────────────▶│
 │                │                 │◀── query_vec ─────────────────│
 │                │                 │── cosine search ──▶│          │
 │                │                 │◀── top-3 chunks ──│          │
 │                │                 │                │              │
 │                │                 │── [context + query] ──────────▶│
 │                │                 │                │   GPT-4-turbo│
 │                │                 │◀── response ──────────────────│
 │                │                 │── INSERT audit_log ──▶│       │
 │                │◀── response ────│                │              │
 │◀─ answer ─────│                  │                │              │
```

### 5.3 Stateful Agent Flow

```
User          Frontend         Python Agent         PostgreSQL
 │                │                 │                    │
 │─ Send query ──▶│                 │                    │
 │                │── POST /api/graph?thread_id=abc ─────▶│
 │                │                 │── load checkpoint ──▶│
 │                │                 │◀── state (messages) │
 │                │                 │                    │
 │                │                 │── call_model node  │
 │                │                 │   (GPT-4o-mini)    │
 │                │                 │── call_tool node   │
 │                │                 │   (if tool_call)   │
 │                │                 │── save checkpoint ──▶│
 │                │◀── response ────│                    │
 │◀─ answer ─────│                  │                    │
```

### 5.4 Multi-Agent Supervisor Flow

```
POST /api/multi-agent { query }
        │
        ▼
SemanticCache.get() ──── HIT ──────────────────▶ return response
        │ MISS
        ▼
Supervisor LLM decides routing
        │
   ┌────┴──────────────────────┐
   ▼           ▼               ▼
Research   Quantitative      Writer
Agent      Agent             Agent
(Tavily/   (yfinance/        (format)
 Exa)      pandas)
   │           │               │
   └────────── ▼ ──────────────┘
          Merged results
               │
               ▼
       SemanticCache.put()
               │
               ▼
          Response { answer, agents_used, cache_hit, latency_ms }
```

### 5.5 HITL Approval Flow

```
User          Frontend          Python Agent        PostgreSQL
 │                │                  │                   │
 │─ "buy AAPL" ──▶│                  │                   │
 │                │── POST /api/graph ▶│                  │
 │                │                  │── call_model      │
 │                │                  │   decides buy_stock│
 │                │                  │── INTERRUPT ──────▶│ (save state)
 │                │◀─ { pending_approval: true } ─────────│
 │                │   { tool: "buy_stock", inputs: {...}} │
 │◀─ approval card│                  │                   │
 │   shown        │                  │                   │
 │─ click Approve ▶│                  │                   │
 │                │── POST /api/graph/approve ────────────▶│
 │                │   { approve: true }    │              │
 │                │                  │◀── restore state ─│
 │                │                  │── call_tool(buy_stock)
 │                │◀─ "Trade executed" ──────────────────-│
 │◀─ result ─────│                   │                   │
```

### 5.6 Generative UI Streaming Flow

```
User          Frontend              Python Agent           OpenAI / yfinance
 │                │                      │                        │
 │─ "AAPL chart" ▶│                      │                        │
 │                │── EventSource ───────▶│                       │
 │                │  /api/generative_ui  │                        │
 │                │                      │── detect visualization │
 │                │                      │── yfinance.download() ──▶│
 │                │                      │◀── price history ───────│
 │                │                      │── build LineChartArtifact│
 │                │◀── SSE: JSON line 1 ─│  { type: "LINE_CHART", │
 │    renders     │   (chart artifact)   │    data: [...] }       │
 │    Recharts    │                      │                        │
 │                │◀── SSE: JSON line 2 ─│  { type: "STOCK_CARD", │
 │    renders     │   (card artifact)   │    price, change, ... }│
 │    card        │                      │                        │
 │                │◀── SSE: [DONE] ──────│                        │
```

---

## 6. Database Schema

### Complete Schema DDL

```sql
-- Enable vector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Document embeddings (RAG)
CREATE TABLE IF NOT EXISTS vector_store (
    id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    content    TEXT NOT NULL,
    embedding  vector(1536),
    metadata   JSONB
);
CREATE INDEX IF NOT EXISTS idx_vector_store_embedding
    ON vector_store USING hnsw (embedding vector_cosine_ops);

-- User accounts
CREATE TABLE IF NOT EXISTS users (
    id          BIGSERIAL PRIMARY KEY,
    username    VARCHAR(50) UNIQUE NOT NULL,
    email       VARCHAR(100) UNIQUE NOT NULL,
    password    TEXT NOT NULL,
    role        VARCHAR(20) NOT NULL DEFAULT 'USER',
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    enabled     BOOLEAN DEFAULT TRUE
);

-- Compliance audit log
CREATE TABLE IF NOT EXISTS chat_audit_logs (
    id               BIGSERIAL PRIMARY KEY,
    user_id          BIGINT REFERENCES users(id),
    user_query       TEXT,
    sanitized_query  TEXT,
    ai_response      TEXT,
    timestamp        TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    pii_detected     BOOLEAN DEFAULT FALSE
);
CREATE INDEX IF NOT EXISTS idx_audit_user_id ON chat_audit_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON chat_audit_logs(timestamp);

-- LangGraph state persistence
CREATE TABLE IF NOT EXISTS checkpoints (
    thread_id      TEXT NOT NULL,
    checkpoint_id  TEXT NOT NULL,
    checkpoint     JSONB NOT NULL,
    metadata       JSONB,
    PRIMARY KEY (thread_id, checkpoint_id)
);

CREATE TABLE IF NOT EXISTS checkpoint_writes (
    thread_id      TEXT NOT NULL,
    checkpoint_id  TEXT NOT NULL,
    task_id        TEXT NOT NULL,
    idx            INTEGER NOT NULL,
    channel        TEXT NOT NULL,
    value          JSONB,
    PRIMARY KEY (thread_id, checkpoint_id, task_id, idx)
);

-- Semantic query cache
CREATE TABLE IF NOT EXISTS semantic_cache (
    query_hash       TEXT PRIMARY KEY,
    query_text       TEXT NOT NULL,
    query_embedding  vector(1536) NOT NULL,
    response_text    TEXT NOT NULL,
    created_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at       TIMESTAMP NOT NULL,
    hit_count        INTEGER DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_semantic_cache_embedding
    ON semantic_cache USING ivfflat (query_embedding vector_cosine_ops);
CREATE INDEX IF NOT EXISTS idx_semantic_cache_expires
    ON semantic_cache(expires_at);
```

---

## 7. API Reference

### Java Backend (Port 8080)

| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/api/auth/register` | None | Register new user |
| POST | `/api/auth/login` | None | Authenticate, get JWT |
| GET | `/api/chat?query=` | JWT | Standard RAG query |
| GET | `/api/chat/agent?query=` | JWT | Route to Python agent |
| POST | `/api/ingest` | JWT | Upload PDF for ingestion |
| GET | `/actuator/health` | None | Service health |
| GET | `/actuator/prometheus` | None | Prometheus metrics |

### Python Agent (Port 8000)

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/` | None | Feature listing |
| GET | `/health` | None | Health + cache status |
| POST | `/api/graph` | None* | Stateful LangGraph query |
| POST | `/api/graph/pending` | None* | Fetch HITL pending approval |
| POST | `/api/graph/approve` | None* | Approve/reject HITL tool |
| GET | `/api/history/{thread_id}` | None* | Conversation history |
| POST | `/api/rewind` | None* | Rewind to past checkpoint |
| POST | `/api/multi-agent` | None* | Multi-agent supervisor query |
| POST | `/api/multi-agent/config` | None* | Update cache config |

\* Python service is internal; authentication handled at Java gateway

#### POST /api/graph

**Request:**
```json
{
  "query": "What is the current price of AAPL?",
  "thread_id": "user-session-uuid",
  "enable_hitl": true
}
```

**Response (normal):**
```json
{
  "response": "Apple Inc. (AAPL) is currently trading at $192.45...",
  "thread_id": "user-session-uuid",
  "pending_approval": false
}
```

**Response (HITL interrupt):**
```json
{
  "response": "I need to execute a trade. Please approve.",
  "thread_id": "user-session-uuid",
  "pending_approval": true,
  "tool_name": "buy_stock",
  "tool_inputs": { "symbol": "AAPL", "quantity": 10, "price": 192.45 }
}
```

#### POST /api/multi-agent

**Request:**
```json
{
  "query": "Compare AAPL vs MSFT earnings and recent news"
}
```

**Response:**
```json
{
  "response": "## AAPL vs MSFT Analysis\n...",
  "agents_used": ["research", "quantitative", "writer"],
  "cache_hit": false,
  "cache_similarity": 0.0,
  "latency_ms": 3420,
  "cost_saved": 0.0
}
```

---

## 8. Architectural Patterns & Decisions

### Pattern Summary

| Pattern | Where Used | Trade-offs |
|---|---|---|
| **Microservices** | Java + Python as separate services | Allows technology heterogeneity; adds network hop |
| **LangGraph StateGraph** | Python agent | Persistent, resumable conversations; requires PostgreSQL |
| **Multi-Agent Supervisor** | Complex research queries | Higher quality via specialization; higher latency |
| **Semantic Caching** | Multi-agent endpoint | Dramatic cost/latency reduction; may serve stale answers |
| **HITL Interrupts** | High-risk tool calls | Compliance and safety; adds round-trip for user |
| **Generative UI (SSE)** | Visualization queries | Rich UX; requires SSE-capable client |
| **Hybrid Search Routing** | All web search | Best-of-both engines with zero LLM cost for routing |
| **Circuit Breaker** | Java → Python calls | Graceful degradation; hides Python failures from users |
| **PII AOP** | All chat input | Invisible, universal sanitization; AOP adds complexity |
| **RAG over Vector DB** | Document queries | Grounded, citable answers; requires ingestion step |
| **JWT Stateless Auth** | All API calls | Scales horizontally; no server-side session store |

### Key Design Decisions

**1. Java for API gateway, Python for AI orchestration**  
Java Spring Boot provides enterprise-grade security, JPA, Spring AI integrations, and robust JVM tooling. Python is the natural home for LangGraph, LangChain, and the AI ecosystem. The circuit breaker between them prevents AI layer failures from cascading to auth or ingestion.

**2. PostgreSQL as the single data store**  
All persistence — vectors, auth, audit, agent state, semantic cache — uses one PostgreSQL instance with the pgvector extension. This reduces operational complexity at the cost of horizontal scaling flexibility. The HNSW and IVFFlat indexes make vector queries fast within this constraint.

**3. Semantic cache threshold at 0.92**  
0.92 cosine similarity is intentionally high to prevent semantically close but factually distinct queries from receiving the same cached response. This is especially important in a compliance context where subtle query differences may require different answers.

**4. Thread-ID multi-tenancy**  
Each conversation receives a UUID `thread_id`. LangGraph's `PostgresSaver` namespaces all checkpoints by this ID, providing full tenant isolation without a complex multi-tenant database schema.

**5. HITL as graph interrupt (not post-hoc review)**  
The LangGraph interrupt mechanism halts execution before the tool runs, not after. This ensures that dangerous operations (stock trades, emails, database deletes) are never executed without explicit approval, satisfying pre-execution compliance requirements.

---

## 9. Security Model

### Threat Model

| Threat | Mitigation |
|---|---|
| Unauthorized API access | JWT authentication on all non-public endpoints |
| PII stored in audit logs | AOP-based sanitization before any DB write |
| Prompt injection | `DataGuardService` pattern detection; `red_team/` automated tests |
| LLM jailbreaking | System prompt hardening; red team CI workflow |
| Agent executing high-risk actions unilaterally | HITL interrupt gates on buy_stock, send_email, delete_db |
| Python service unavailable | Resilience4j circuit breaker with graceful fallback |
| Container credential exposure | Secrets in GitHub Actions, not in code; .env in .gitignore |

### Red Team CI

[.github/workflows/red-team-security.yml](.github/workflows/red-team-security.yml) runs automated adversarial tests:
- Prompt injection attempts
- Jailbreak payloads
- PII leakage probes
- Data exfiltration scenarios

Pipeline fails on critical findings, blocking merge to main.

---

## 10. Scalability & Performance

### Current Bottlenecks

| Component | Bottleneck | Mitigation |
|---|---|---|
| pgvector | Single-node; HNSW index held in RAM | Semantic cache reduces query frequency |
| OpenAI API | Rate limits; per-token cost | Semantic cache; gpt-4o-mini for agents |
| Java backend | Single container | Stateless JWT → horizontal scale with load balancer |
| Python agent | Single Uvicorn worker | `uvicorn --workers N` or gunicorn process manager |

### Semantic Cache Impact

| Metric | No Cache | With Cache (0.92 threshold) |
|---|---|---|
| LLM call latency | ~2000 ms | <10 ms (cache hit) |
| Cost per request | ~$0.03 | $0.00 (cache hit) |
| Cache TTL | — | 300 seconds |

### Vector Search Performance

| Index | Build Time | Query Time | Recall |
|---|---|---|---|
| HNSW (vector_store) | Slower | Fastest | ~99% |
| IVFFlat (semantic_cache) | Fast | Fast | ~95% |

### Future Scaling Path

1. **Read replicas** for PostgreSQL (route all SELECT queries to replica)
2. **Dedicated pgvector node** (separate from OLTP data)
3. **Redis** for JWT session blacklisting and rate limiting
4. **Kubernetes** + Horizontal Pod Autoscaler for Java and Python services
5. **CDN** in front of Next.js for static asset caching

---

## 11. Configuration Reference

### Environment Variables

| Variable | Service | Description |
|---|---|---|
| `OPENAI_API_KEY` | Java + Python | OpenAI API authentication |
| `TAVILY_API_KEY` | Python | Tavily search API |
| `EXA_API_KEY` | Python | Exa search API |
| `DATABASE_URL` | Python | PostgreSQL connection string |
| `LANGCHAIN_API_KEY` | Python | LangSmith observability |
| `LANGCHAIN_TRACING_V2` | Python | Enable LangSmith tracing (`true`) |
| `SEMANTIC_CACHE_ENABLED` | Python | Toggle caching (`true`/`false`) |
| `SEMANTIC_CACHE_TTL` | Python | Cache TTL in seconds (default: 300) |
| `SEMANTIC_CACHE_THRESHOLD` | Python | Cosine similarity threshold (default: 0.92) |
| `SPRING_DATASOURCE_URL` | Java | JDBC connection string |
| `PYTHON_AGENT_URL` | Java | Python service URL |
| `NEXT_PUBLIC_API_URL` | Frontend | Java backend URL |

### Docker Compose Port Map

| Service | Container Port | Host Port |
|---|---|---|
| PostgreSQL | 5432 | 5432 |
| Python Agent | 8000 | 8000 |
| Java Backend | 8080 | 8080 |
| Frontend | 3000 | 3000 |
| Prometheus | 9090 | 9090 |
| Grafana | 3001 | 3001 |

### Service Dependencies (startup order)

```
postgres
  └──▶ python-agent (depends_on: postgres)
         └──▶ java-backend (depends_on: postgres, python-agent)
                └──▶ frontend (depends_on: java-backend)

prometheus (independent)
grafana (depends_on: prometheus)
```

---

*End of System Design Document*
