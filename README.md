# Enterprise RAG Platform 🤖

> **AI Solutions Architect Portfolio Project**  
> Production-grade AI system demonstrating enterprise-ready agentic architecture

AI-powered compliance and knowledge management system with document ingestion, vector search, and intelligent chat capabilities featuring **stateful agents with PostgreSQL-backed state persistence**.

## 🚀 **Key Architectural Highlights**

### **Production-Grade Agentic Patterns**
- ✅ **State Persistence**: Conversations survive container restarts (PostgreSQL checkpointer)
- ✅ **Time-Travel Debugging**: Rewind to any checkpoint, explore alternate paths
- ✅ **Multi-Tenant Isolation**: Independent conversation threads per user
- ✅ **Human-in-the-Loop (HITL)**: Interrupt pattern for high-risk tool approvals
- ✅ **Cognitive Architecture**: LangGraph with tool orchestration, not just simple search
- ✅ **LLM Evaluation**: LangSmith integration with 20-question regression testing in CI/CD

📖 **[State Persistence Architecture Guide →](agent-python/STATE_PERSISTENCE_README.md)**  
🔐 **[Human-in-the-Loop (HITL) Guide →](agent-python/HITL_README.md)**  
📊 **[LangSmith Evaluation & Observability →](agent-python/EVALUATION_README.md)**

---

## Architecture

### System Overview

```
                    ┌─────────────────────────────┐
                    │      End Users              │
                    │   (Web Browser/API)         │
                    └──────────────┬──────────────┘
                                   │ HTTPS
                                   ▼
                    ┌──────────────────────────────┐
                    │    Nginx Reverse Proxy       │
                    │    (Port 80/443)             │
                    │    - SSL/TLS termination     │
                    │    - Load balancing          │
                    └─────────┬────────────────────┘
                              │
                    ┌─────────┴──────────┐
                    │                    │
                    ▼                    ▼
        ┌───────────────────┐  ┌──────────────────┐
        │   Frontend        │  │   Backend API    │
        │   Next.js 14      │  │   Spring Boot    │
        │   (Port 3000)     │  │   (Port 8080)    │
        │                   │  │                  │
        │ • React UI        │  │ • REST APIs      │
        │ • Auth Context    │  │ • JWT Auth       │
        │ • Tailwind CSS    │  │ • Spring AI      │
        └───────────────────┘  └────────┬─────────┘
                                        │
                        ┌───────────────┼───────────────┐
                        │               │               │
                        ▼               ▼               ▼
            ┌─────────────────┐ ┌──────────────┐ ┌────────────┐
            │ Python Agent    │ │  PostgreSQL  │ │  OpenAI    │
            │ LangGraph v2    │ │  + pgvector  │ │    API     │
            │ (Port 8000)     │ │  (Port 5432) │ │            │
            │                 │ │              │ │            │
            │ • LangChain     │ │ • User DB    │ │ • GPT-4    │
            │ • DuckDuckGo    │ │ • Vectors    │ │ • Embed    │
            │ • State Persist │ │ • Checkpoints│ │            │
            └─────────────────┘ └──────────────┘ └────────────┘
                    ↑                   ↑
                    └───────────────────┘
                      AsyncPostgresSaver
                    (Time-Travel Layer)
```

### Data Flow

**1. Hybrid RAG + Agent Flow:**
```
User Query → Frontend → Backend (Spring Boot)
                          │
                          ├→ Check Vector Store
                          │
                          ├─ Has Documents? → Yes → RAG Pipeline
                          │                          │
                          │                          ├→ Similarity Search (pgvector)
                          │                          ├→ Retrieve Context
                          │                          └→ LLM Generation (GPT-4)
                          │
                          └─ No Documents? → Python Agent
                                              │
                                              ├→ LangGraph Workflow
                                              ├→ Tool Selection (DuckDuckGo)
                                              ├→ Web Search
                                              └→ Answer Synthesis
```

**2. Document Ingestion Flow:**
```
PDF Upload → Backend → Extract Text → Chunk Content → Generate Embeddings (OpenAI)
                                                            │
                                                            ▼
                                                    Store in pgvector
                                                            │
                                                            ▼
                                                    Ready for RAG Queries
```

### Security Architecture

```
Request → Nginx (SSL) → Backend → JWT Validation → PII Sanitization
                                                          │
                                                          ├→ Aspect-Oriented (AOP)
                                                          ├→ Regex Detection
                                                          ├→ Auto Masking
                                                          └→ Audit Logging
```

## Features

- 💬 **Intelligent Chat**: AI-powered conversations with context from your documents
- 📄 **Document Ingestion**: Upload and process PDF documents
- 🔍 **Vector Search**: Semantic search using pgvector
- 🧠 **LangGraph Agents**: Advanced AI workflows with Python
- 🛡️ **PII Sanitization**: Automatic detection and masking of sensitive data
- 📊 **Audit Logging**: Track all interactions and queries
- 🔄 **Circuit Breaker**: Resilient service communication

## Tech Stack

### Frontend
- Next.js 14 (App Router)
- TypeScript
- Tailwind CSS
- Axios

### Backend
- Java 17 + Spring Boot 3.x
- Spring AI (OpenAI integration)
- PostgreSQL + pgvector
- Hibernate/JPA

### AI/ML
- Python 3.11
- LangChain + LangGraph
- OpenAI GPT-4
- FastAPI

### Infrastructure
- Docker + Docker Compose
- AWS EC2
- Nginx (reverse proxy)

## Quick Start

### Prerequisites
- Docker & Docker Compose
- OpenAI API key
- (Optional) LangSmith API key for tracing

### 1. Clone the Repository

```bash
git clone https://github.com/anupam1708/enterprise-rag-platform.git
cd enterprise-rag-platform
```

### 2. Set Up Environment Variables

```bash
# Root .env file
echo "OPENAI_API_KEY=your-key-here" > .env

# Python agent .env
cp agent-python/.env.example agent-python/.env
# Edit agent-python/.env and add your OpenAI key

# Frontend .env
cp frontend-nextjs/.env.example frontend-nextjs/.env
# Edit if needed (defaults to http://localhost:8080)
```

### 3. Start All Services

```bash
docker-compose up -d
```

Wait for all services to start (~30 seconds), then verify:

```bash
docker ps
```

You should see 4 containers running:
- `rag_frontend` (port 3000)
- `java_backend` (port 8080)
- `python_agent` (port 8000)
- `compliance_db` (port 5432)

### 4. Access the Application

- **Frontend UI**: http://localhost:3000
- **Backend API**: http://localhost:8080
- **Python Agent API Docs**: http://localhost:8000/docs

## API Endpoints

### Authentication

#### Register New User
```bash
POST /api/auth/register
Content-Type: application/json

{
  "username": "john_doe",
  "email": "john@example.com",
  "password": "SecurePass123!"
}

# Response (201 Created)
{
  "token": "eyJhbGciOiJIUzI1NiJ9...",
  "username": "john_doe",
  "email": "john@example.com",
  "role": "USER"
}
```

#### Login
```bash
POST /api/auth/login
Content-Type: application/json

{
  "username": "john_doe",
  "password": "SecurePass123!"
}

# Response (200 OK)
{
  "token": "eyJhbGciOiJIUzI1NiJ9...",
  "username": "john_doe",
  "email": "john@example.com",
  "role": "USER"
}
```

### Chat Endpoints

#### 1. Hybrid Chat (Recommended)
Intelligent routing: uses RAG when documents exist, falls back to web search when empty.

```bash
GET /api/chat?query=your-question
Authorization: Bearer <jwt-token>

# Example: Question about uploaded documents
curl -X GET "http://localhost:8080/api/chat?query=What%20are%20the%20compliance%20requirements" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiJ9..."

# Response (200 OK)
"According to the uploaded compliance document, the key requirements are: 
1. Annual audits, 2. Data encryption at rest..."
```

**Behavior:**
- ✅ **Documents exist** → RAG Pipeline (vector search + GPT-4)
- ❌ **No documents** → Python LangGraph Agent (web search)

#### 2. Direct Agent Chat
Always uses Python LangGraph agent with DuckDuckGo search.

```bash
GET /api/chat/agent?query=your-question
Authorization: Bearer <jwt-token>

# Example: General knowledge question
curl -X GET "http://localhost:8080/api/chat/agent?query=Who%20is%20the%20current%20PM%20of%20Canada" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiJ9..."

# Response (200 OK)
"Justin Trudeau is the current Prime Minister of Canada..."
```

**Use Cases:**
- Real-time information lookup
- General knowledge questions
- When you want to force web search

### Document Management

#### Upload Document
```bash
POST /api/ingest/upload
Authorization: Bearer <jwt-token>
Content-Type: multipart/form-data

# Using curl
curl -X POST "http://localhost:8080/api/ingest/upload" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiJ9..." \
  -F "file=@/path/to/document.pdf"

# Response (200 OK)
"✅ Document uploaded and processed successfully! 
Added 42 chunks to vector store."
```

**Supported Formats:**
- PDF (`.pdf`)
- Max size: 10MB

**Processing Steps:**
1. Extract text from PDF
2. Split into semantic chunks (500 tokens, 100 overlap)
3. Generate embeddings (OpenAI text-embedding-ada-002)
4. Store in PostgreSQL with pgvector

#### List Documents
```bash
GET /api/ingest/documents
Authorization: Bearer <jwt-token>

# Response (200 OK)
[
  {
    "id": "uuid-123",
    "filename": "compliance_guide.pdf",
    "uploadedAt": "2026-01-27T10:30:00Z",
    "chunks": 42,
    "size": "2.3MB"
  }
]
```

### Health & Monitoring

#### Health Check
```bash
GET /actuator/health

# Response (200 OK)
{
  "status": "UP",
  "components": {
    "db": {"status": "UP"},
    "circuitBreakers": {"status": "UP"},
    "pythonAgent": {"status": "UP"}
  }
}
```

#### Metrics (Prometheus)
```bash
GET /actuator/prometheus

# Returns Prometheus-formatted metrics
# - HTTP request latencies
# - JVM memory usage
# - Circuit breaker states
# - Database connection pool
```

### Error Responses

```json
// 401 Unauthorized
{
  "timestamp": "2026-01-27T10:30:00.000+00:00",
  "status": 401,
  "error": "Unauthorized",
  "message": "JWT token expired or invalid",
  "path": "/api/chat"
}

// 500 Internal Server Error
{
  "timestamp": "2026-01-27T10:30:00.000+00:00",
  "status": 500,
  "error": "Internal Server Error",
  "message": "Circuit breaker is OPEN - Python agent unavailable",
  "path": "/api/chat/agent"
}
```

## Development

### Run Locally (without Docker)

#### Backend (Java)
```bash
cd backend-java
./mvnw spring-boot:run
```

#### Python Agent
```bash
cd agent-python
pip install -r requirements.txt
uvicorn main:app --reload
```

#### Frontend
```bash
cd frontend-nextjs
npm install
npm run dev
```

### Database Migrations

The database schema is automatically created on startup. To reset:

```bash
docker-compose down -v  # Warning: deletes all data
docker-compose up -d
```

## Deployment

### Local Development Setup

#### Prerequisites
```bash
# Required Software
- Docker Desktop (v24.0+)
- Docker Compose (v2.20+)
- Git
- OpenAI API Key

# Optional (for local development without Docker)
- Node.js 18+
- Java 17+
- Maven 3.8+
- Python 3.11+
- PostgreSQL 16
```

#### Step-by-Step Local Setup

**1. Clone Repository**
```bash
git clone https://github.com/anupam1708/enterprise-rag-platform.git
cd enterprise-rag-platform
```

**2. Configure Environment Variables**

Create `.env` in project root:
```bash
# OpenAI Configuration
OPENAI_API_KEY=sk-proj-your-actual-key-here

# Database (Docker automatically configures these)
POSTGRES_USER=postgres
POSTGRES_PASSWORD=password
POSTGRES_DB=compliance_db
```

Create `agent-python/.env`:
```bash
OPENAI_API_KEY=sk-proj-your-actual-key-here

# Optional: LangSmith Tracing
LANGCHAIN_TRACING_V2=false
# LANGCHAIN_API_KEY=your-langsmith-key
# LANGCHAIN_PROJECT=enterprise-rag
```

Create `frontend-nextjs/.env.local`:
```bash
NEXT_PUBLIC_API_URL=http://localhost:8080
```

**3. Start All Services**
```bash
# Build and start all containers
docker-compose up -d

# Wait ~30 seconds for services to initialize
# Check status
docker-compose ps

# View logs
docker-compose logs -f
```

**4. Verify Deployment**
```bash
# Check all containers are running
docker ps

# Test backend health
curl http://localhost:8080/actuator/health

# Test Python agent
curl http://localhost:8000/docs

# Access frontend
open http://localhost:3000
```

**5. Create First User**
```bash
curl -X POST "http://localhost:8080/api/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "admin",
    "email": "admin@example.com",
    "password": "SecurePass123!"
  }'
```

---

### AWS EC2 Production Deployment

#### Infrastructure Setup

**1. Launch EC2 Instance**
```bash
# Recommended Configuration:
- AMI: Ubuntu 24.04 LTS
- Instance Type: t3.medium (2 vCPU, 4GB RAM) minimum
                 t3.large (2 vCPU, 8GB RAM) recommended for production
- Storage: 30GB GP3 SSD
- Security Group: See configuration below
```

**2. Configure Security Group**
```bash
# Inbound Rules
Type            Protocol    Port Range    Source          Description
SSH             TCP         22            Your IP         SSH access
HTTP            TCP         80            0.0.0.0/0       HTTP traffic
HTTPS           TCP         443           0.0.0.0/0       HTTPS traffic
Custom TCP      TCP         8080          0.0.0.0/0       Backend API (optional)
Custom TCP      TCP         3000          0.0.0.0/0       Frontend (optional)

# Outbound Rules
All traffic     All         All           0.0.0.0/0       Allow all outbound
```

**3. Connect to EC2 Instance**
```bash
# Download your key pair (e.g., rag-key.pem)
chmod 400 rag-key.pem

# Connect via SSH
ssh -i rag-key.pem ubuntu@<your-ec2-public-ip>
```

#### Server Setup

**4. Install Dependencies**
```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Docker
sudo apt install -y docker.io docker-compose
sudo systemctl start docker
sudo systemctl enable docker

# Add ubuntu user to docker group
sudo usermod -aG docker ubuntu
newgrp docker

# Verify installation
docker --version
docker-compose --version
```

**5. Deploy Application**
```bash
# Clone repository (recommended approach)
cd ~
git clone https://github.com/anupam1708/enterprise-rag-platform.git
cd enterprise-rag-platform

# OR: Use SCP to copy files
# scp -i rag-key.pem -r ./enterprise-rag-platform ubuntu@<ip>:~/

# Configure environment variables
nano .env
# Add your OpenAI API key and other configs

nano agent-python/.env
# Add your OpenAI API key

# Update frontend environment for production
nano docker-compose.yml
# Change NEXT_PUBLIC_API_URL to your domain or IP
```

**6. Start Services**
```bash
# Build and start containers
docker-compose up -d

# Monitor startup
docker-compose logs -f

# Verify all containers are running
docker ps
```

#### Domain & SSL Setup

**7. Configure Domain (Optional but Recommended)**

**A. Point Domain to EC2**
```bash
# In your DNS provider (e.g., Namecheap, Cloudflare)
# Create A record:
Type: A
Name: @ (or www)
Value: <your-ec2-elastic-ip>
TTL: 300
```

**B. Install Nginx**
```bash
sudo apt install -y nginx
sudo systemctl start nginx
sudo systemctl enable nginx
```

**C. Configure Nginx Reverse Proxy**
```bash
sudo nano /etc/nginx/sites-available/default
```

Add this configuration:
```nginx
server {
    listen 80;
    server_name your-domain.com www.your-domain.com;

    # Frontend
    location / {
        proxy_pass http://localhost:3000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
    }

    # Backend API
    location /api {
        proxy_pass http://localhost:8080;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Actuator endpoints
    location /actuator {
        proxy_pass http://localhost:8080;
    }
}
```

Test and reload:
```bash
sudo nginx -t
sudo systemctl reload nginx
```

**D. Install SSL Certificate (Let's Encrypt)**
```bash
# Install Certbot
sudo apt install -y certbot python3-certbot-nginx

# Obtain certificate
sudo certbot --nginx -d your-domain.com -d www.your-domain.com

# Follow prompts:
# - Enter email
# - Agree to terms
# - Choose redirect HTTP to HTTPS (option 2)

# Verify auto-renewal
sudo certbot renew --dry-run
```

**E. Update Frontend Environment**
```bash
# Update docker-compose.yml with your domain
cd ~/enterprise-rag-platform
nano docker-compose.yml

# Change NEXT_PUBLIC_API_URL:
# from: http://localhost:8080
# to: https://your-domain.com

# Rebuild frontend
docker-compose build frontend
docker-compose up -d frontend
```

#### Database Backup

**8. Configure Automated Backups**
```bash
# Create backup script
sudo nano /usr/local/bin/backup-postgres.sh
```

Add this script:
```bash
#!/bin/bash
BACKUP_DIR="/home/ubuntu/backups"
DATE=$(date +%Y%m%d_%H%M%S)
mkdir -p $BACKUP_DIR

docker exec compliance_db pg_dump -U postgres compliance_db | gzip > $BACKUP_DIR/backup_$DATE.sql.gz

# Keep only last 7 days of backups
find $BACKUP_DIR -name "backup_*.sql.gz" -mtime +7 -delete
```

Make executable and schedule:
```bash
sudo chmod +x /usr/local/bin/backup-postgres.sh

# Add to crontab (daily at 2 AM)
crontab -e
# Add line:
0 2 * * * /usr/local/bin/backup-postgres.sh
```

#### Monitoring & Maintenance

**9. Set Up Log Rotation**
```bash
# Docker logs can grow large
sudo nano /etc/docker/daemon.json
```

Add:
```json
{
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "10m",
    "max-file": "3"
  }
}
```

Restart Docker:
```bash
sudo systemctl restart docker
docker-compose up -d
```

**10. Monitor Services**
```bash
# View logs
docker-compose logs -f [service-name]

# Check resource usage
docker stats

# Check disk space
df -h

# View container health
docker ps
docker inspect <container-id> | grep Health
```

---

### Production Checklist

Before going live, ensure:

- [ ] **Security**
  - [ ] SSL/HTTPS configured and tested
  - [ ] JWT secret changed from default
  - [ ] Database password changed from default
  - [ ] Security group restricts SSH to your IP
  - [ ] OpenAI API key stored securely (AWS Secrets Manager)
  - [ ] Rate limiting configured on Nginx

- [ ] **Monitoring**
  - [ ] CloudWatch agent installed
  - [ ] Prometheus metrics accessible
  - [ ] Error alerting configured
  - [ ] Log aggregation set up

- [ ] **Backup & Recovery**
  - [ ] Automated database backups scheduled
  - [ ] Backup restoration tested
  - [ ] EBS snapshot schedule configured

- [ ] **Performance**
  - [ ] Load testing completed
  - [ ] Database indexes optimized
  - [ ] CDN configured for static assets
  - [ ] Connection pooling tuned

- [ ] **High Availability** (Optional)
  - [ ] Multi-AZ deployment
  - [ ] Load balancer configured
  - [ ] Auto-scaling group set up
  - [ ] Database replicas configured

---

### Scaling Considerations

**Horizontal Scaling:**
```bash
# Scale specific services
docker-compose up -d --scale java-backend=3

# Use AWS Application Load Balancer
# - Distribute traffic across multiple EC2 instances
# - Enable health checks
# - Configure sticky sessions for WebSocket
```

**Database Scaling:**
```bash
# Use Amazon RDS for PostgreSQL
# - Automated backups
# - Read replicas for query performance
# - Multi-AZ for high availability

# Connection pooling (already configured in Spring Boot)
spring.datasource.hikari.maximum-pool-size=20
spring.datasource.hikari.minimum-idle=10
```

**Caching Strategy:**
```bash
# Add Redis for caching
# - Cache frequently accessed documents
# - Session storage
# - Rate limiting counters

docker-compose.yml:
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
```

## Project Structure

```
enterprise-rag-platform/
├── frontend-nextjs/          # Next.js frontend
│   ├── app/                  # App router pages
│   ├── components/           # React components
│   └── Dockerfile
├── backend-java/             # Spring Boot backend
│   ├── src/main/java/        # Java source code
│   ├── src/main/resources/   # Application config
│   └── Dockerfile
├── agent-python/             # Python AI agent
│   ├── agent.py             # LangGraph agent
│   ├── main.py              # FastAPI server
│   └── Dockerfile
├── docker-compose.yml        # Multi-container orchestration
└── init-db.sql              # Database initialization
```

## Troubleshooting

### Frontend can't connect to backend
- Check that `NEXT_PUBLIC_API_URL` is set correctly
- In browser, update to use public IP instead of `localhost`
- Verify backend is accessible: `curl http://localhost:8080/api/chat/agent?query=test`

### Document upload fails
- Ensure pgvector extension is enabled: `docker exec compliance_db psql -U postgres -d compliance_db -c "CREATE EXTENSION IF NOT EXISTS vector;"`
- Check backend logs: `docker logs java_backend`

### LangSmith tracing timeouts
- Verify DNS resolution in container: `docker exec python_agent python -c "import socket; print(socket.gethostbyname('api.smith.langchain.com'))"`
- Or disable tracing: Set `LANGCHAIN_TRACING_V2=false` in `agent-python/.env`

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## License

MIT License - see LICENSE file for details

## Contact

- GitHub: [@anupam1708](https://github.com/anupam1708)
- Repository: https://github.com/anupam1708/enterprise-rag-platform
