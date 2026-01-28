# Enterprise RAG Platform 🤖

AI-powered compliance and knowledge management system with document ingestion, vector search, and intelligent chat capabilities.

## Architecture

```
┌─────────────────┐
│  Frontend       │ ← Next.js 14 + TypeScript + Tailwind
│  (Port 3000)    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Java Backend   │ ← Spring Boot + Spring AI
│  (Port 8080)    │
└────────┬────────┘
         │
    ┌────┴────┐
    ▼         ▼
┌─────────┐ ┌──────────────┐
│ Python  │ │  PostgreSQL  │
│ Agent   │ │  + pgvector  │
│ (8000)  │ │  (5432)      │
└─────────┘ └──────────────┘
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

### Chat Endpoints

#### 1. Hybrid Chat (RAG + Agent)
Checks vector database for context first. If no documents found, routes to Python LangGraph agent with web search.

```bash
GET /api/chat?query=your-question
Authorization: Bearer <jwt-token>
```

**Behavior:**
- ✅ Documents in vector DB → Uses RAG (vector search + LLM)
- ❌ No documents → Routes to Python agent with DuckDuckGo search

#### 2. Direct Agent Chat
Always uses Python LangGraph agent with search tools, bypassing vector database.

```bash
GET /api/chat/agent?query=your-question
Authorization: Bearer <jwt-token>
```

**Use Cases:**
- General knowledge questions
- Real-time information lookup
- When you want to force web search

### Document Ingestion
```bash
POST /api/ingest/upload
Authorization: Bearer <jwt-token>
Content-Type: multipart/form-data
Body: file=document.pdf
```

### Authentication
```bash
# Register
POST /api/auth/register
Content-Type: application/json
Body: {"username":"user","email":"user@example.com","password":"password123"}

# Login
POST /api/auth/login
Content-Type: application/json
Body: {"username":"user","password":"password123"}
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

### AWS EC2 Deployment

1. **Launch EC2 Instance** (Ubuntu 22.04, t2.medium or larger)

2. **Install Docker**:
```bash
sudo apt update
sudo apt install -y docker.io docker-compose
sudo usermod -aG docker ubuntu
```

3. **Clone and Configure**:
```bash
git clone https://github.com/anupam1708/enterprise-rag-platform.git
cd enterprise-rag-platform
# Set up .env files as described above
```

4. **Configure Security Group**: Allow inbound traffic on ports:
   - 3000 (Frontend)
   - 8080 (Backend API)
   - 8000 (Python Agent - optional)

5. **Start Services**:
```bash
docker-compose up -d
```

6. **Access**: `http://YOUR_EC2_IP:3000`

### Production Considerations

- [ ] Set up HTTPS with SSL certificates (Let's Encrypt)
- [ ] Configure reverse proxy (Nginx)
- [ ] Use AWS Secrets Manager for API keys
- [ ] Set up CloudWatch for monitoring
- [ ] Configure automated backups for PostgreSQL
- [ ] Implement rate limiting
- [ ] Add authentication (JWT)

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
