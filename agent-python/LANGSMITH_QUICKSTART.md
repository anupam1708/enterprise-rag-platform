# LangSmith Setup - Quick Start

## 1. Get Your API Key (2 minutes)

1. Visit: https://smith.langchain.com/
2. Sign up with GitHub (free tier: 5,000 traces/month)
3. Go to: Settings → API Keys
4. Click "Create API Key"
5. Copy the key (starts with `lsv2_...`)

## 2. Configure Locally

```bash
cd agent-python
cp .env.example .env
# Edit .env
```

Add to `.env`:
```bash
# LangSmith Configuration
LANGCHAIN_TRACING_V2=true
LANGCHAIN_ENDPOINT="https://api.smith.langchain.com"
LANGCHAIN_API_KEY="lsv2_pt_your-key-here"
LANGCHAIN_PROJECT="agent-python"
```

## 3. Test Tracing

```bash
# Start services
cd ..
docker-compose up -d

# Make a request
curl -X POST http://localhost:8000/api/graph \
  -H "Content-Type: application/json" \
  -d '{"query": "What is the capital of France?", "thread_id": "test-123"}'

# Check LangSmith Dashboard
# You should see: https://smith.langchain.com/public/YOUR-PROJECT/r
```

## 4. Run Evaluation

```bash
cd agent-python
python evaluate_agent.py
```

**Expected Output:**
```
🎯 Agent Evaluation - Golden Questions Dataset
📚 Loading dataset from evaluation_dataset.json
✅ Dataset ready with 20 questions
🤖 Running agent: What is the CEO of Google?...
✅ Correct: 'sundar pichai' found in answer
...
✅ Evaluation complete!
📊 View results at: https://smith.langchain.com
```

## 5. Configure CI/CD

**Add GitHub Secrets**:

1. Go to: Your Repo → Settings → Secrets and variables → Actions
2. Click "New repository secret"
3. Add:
   - Name: `LANGCHAIN_API_KEY`
   - Value: Your LangSmith API key

**Done!** Next push to `main` will run evaluations automatically.

## 🎯 What You'll See in LangSmith

### Traces View
- **Input**: User query
- **Steps**: Each agent decision (think, call_tool, respond)
- **Tools Used**: Which tools were called (search, buy_stock, etc.)
- **Latency**: Time per step
- **Errors**: If any step failed

### Datasets View
- **golden-questions**: Your 20 test questions
- **Experiments**: Evaluation runs over time
- **Metrics**: Correctness, latency trends

### Example Trace
```
Thread: test-123
├─ agent (2.3s)
│  ├─ think: "I need to search for France capital"
│  ├─ call_tool: search(query="capital of France")
│  │  └─ result: "Paris is the capital..."
│  └─ respond: "The capital of France is Paris."
└─ Total: 2.3s, Success ✅
```

## 🔧 Troubleshooting

### "No traces showing up"
```bash
# Check env vars are loaded
docker exec enterprise-rag-platform-python-agent-1 env | grep LANGCHAIN

# Should see:
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=lsv2_...
```

### "API key invalid"
- Make sure key starts with `lsv2_pt_`
- No quotes in `.env` file
- Restart containers: `docker-compose restart python-agent`

### "Dataset not found"
```bash
# Re-run evaluation to create it
python evaluate_agent.py
```

## 📊 Understanding Evaluation Results

**Correctness Score**:
- 1.0 = Perfect match
- 0.0 = Completely wrong
- 0.7 = Partially correct

**Embedding Distance**:
- 0.0 = Identical meaning
- 0.3 = Similar meaning
- 1.0 = Completely different

**Good Performance**:
- Correctness > 0.8 (80%+ questions correct)
- Avg latency < 3s
- Error rate < 5%

**Regression Detected**:
- Correctness drops > 10%
- Latency increases > 50%
- New error patterns

## 🎓 Next Steps

1. **Add domain-specific questions** to `evaluation_dataset.json`
2. **Run evaluation locally** before pushing code
3. **Check LangSmith dashboard** after CI/CD runs
4. **Iterate based on failures** - fix questions the agent gets wrong

---

**Pro Tip**: Star ⭐ interesting traces in LangSmith to create a "highlight reel" for portfolio demos!
