# 🚀 Quick Start: State Persistence

Get your production-grade stateful agent running in 5 minutes.

---

## Prerequisites

- Docker & Docker Compose installed
- OpenAI API key

---

## Step 1: Configure Environment

```bash
cd agent-python
cp .env.example .env
nano .env  # Add your OPENAI_API_KEY
```

Your `.env` should look like:
```env
OPENAI_API_KEY=sk-...your-key-here...
DATABASE_URL=postgresql://postgres:password@postgres:5432/compliance_db
```

---

## Step 2: Rebuild and Start Services

```bash
cd ..  # Back to project root
docker-compose down
docker-compose up --build python-agent postgres
```

Wait for:
```
✅ Checkpointer initialized and tables verified
INFO:     Application startup complete.
```

---

## Step 3: Test Basic Functionality

### Test 1: Health Check
```bash
curl http://localhost:8000/health
```

Expected:
```json
{"status": "healthy", "version": "2.0.0"}
```

### Test 2: Stateful Conversation
```bash
# First query
curl -X POST http://localhost:8000/api/graph \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What is the capital of France?",
    "thread_id": "quick-test"
  }'
```

Expected response:
```json
{
  "answer": "The capital of France is Paris.",
  "thread_id": "quick-test"
}
```

### Test 3: Context Preservation
```bash
# Follow-up (should remember Paris)
curl -X POST http://localhost:8000/api/graph \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What is its population?",
    "thread_id": "quick-test"
  }'
```

Expected: Answer about Paris population (mentioning "Paris" or contextually answering about the French capital without asking which city)

Example response:
```json
{
  "answer": "As of the latest data, the population of Paris is approximately 2.2 million people within the city limits...",
  "thread_id": "quick-test"
}
```

---

## Step 4: Run Full Test Suite

```bash
cd agent-python

# Install test dependencies (local)
pip install requests

# Run tests
python test_state_persistence.py
```

You should see:
```
🚀 ======================================================================
  State Persistence Test Suite
  Validating Production-Grade Agentic Architecture
======================================================================

✅ Service is healthy

============================================================
  TEST 1: Stateful Conversation
============================================================
...
🎉 ALL TESTS COMPLETED
```

---

## Step 5: Verify Persistence (Container Restart)

```bash
# Create a conversation
curl -X POST http://localhost:8000/api/graph \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Remember: my favorite color is blue",
    "thread_id": "persistence-test"
  }'

# Restart the container
docker-compose restart python-agent

# Wait 10 seconds, then test
sleep 10

# Ask if it remembers
curl -X POST http://localhost:8000/api/graph \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What is my favorite color?",
    "thread_id": "persistence-test"
  }'
```

✅ If it says "blue", persistence works!

---

## Step 6: Explore Advanced Features

### View Conversation History
```bash
curl -X POST http://localhost:8000/api/graph/history \
  -H "Content-Type: application/json" \
  -d '{
    "thread_id": "quick-test",
    "limit": 5
  }'
```

### Time-Travel Rewind
```bash
curl -X POST http://localhost:8000/api/graph/rewind \
  -H "Content-Type: application/json" \
  -d '{
    "thread_id": "quick-test",
    "steps_back": 1
  }'
```

---

## 🐛 Troubleshooting

### Issue: "Import could not be resolved"
**Solution:** These are just linter warnings. The packages are installed in Docker, not locally.

### Issue: Connection refused to port 8000
**Solution:** Check if the container is running:
```bash
docker ps | grep python_agent
docker logs python_agent
```

### Issue: Database connection error
**Solution:** Ensure PostgreSQL is running:
```bash
docker ps | grep compliance_db
docker logs compliance_db
```

### Issue: Tables not created
**Solution:** The checkpointer auto-creates tables. Check logs:
```bash
docker logs python_agent | grep -i checkpoint
```

You should see:
```
✅ Checkpointer initialized and tables verified
```

---

## 📊 Verify Database Tables

```bash
# Access PostgreSQL
docker exec -it compliance_db psql -U postgres -d compliance_db

# Check tables
\dt

# Should show:
# checkpoints
# checkpoint_writes
# (plus existing tables)

# Query checkpoints
SELECT thread_id, checkpoint_id, metadata 
FROM checkpoints 
ORDER BY checkpoint_id DESC 
LIMIT 5;

# Exit
\q
```

---

## 🎯 Success Criteria

- ✅ Health endpoint returns version 2.0.0
- ✅ Agent remembers context across queries
- ✅ State persists after container restart
- ✅ History endpoint returns checkpoints
- ✅ Rewind endpoint works without errors
- ✅ Multiple thread_ids are isolated

---

## 📚 Next Steps

1. **Read the Architecture Guide:**
   - [STATE_PERSISTENCE_README.md](STATE_PERSISTENCE_README.md)

2. **Compare Before/After:**
   - [ARCHITECTURE_COMPARISON.md](ARCHITECTURE_COMPARISON.md)

3. **Review Implementation:**
   - [IMPLEMENTATION_SUMMARY.md](IMPLEMENTATION_SUMMARY.md)

4. **Prepare for Interviews:**
   - Review talking points in STATE_PERSISTENCE_README.md
   - Practice explaining the architecture

---

## 🆘 Need Help?

**Check logs:**
```bash
docker logs python_agent
docker logs compliance_db
```

**Restart everything:**
```bash
docker-compose down
docker-compose up --build
```

**Access database directly:**
```bash
docker exec -it compliance_db psql -U postgres -d compliance_db
```

---

**Status:** You're now running a **production-grade stateful AI agent** with PostgreSQL-backed persistence! 🎉

This demonstrates Senior AI Solutions Architect capabilities. Use this in your portfolio to show you understand operational concerns like resilience, observability, and multi-tenancy.
