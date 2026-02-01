# LangSmith Evaluation & Observability

> **Portfolio Differentiator**: Moving beyond system metrics (Prometheus/Grafana) to **LLM-specific evaluation** - demonstrating understanding of non-deterministic system testing.

## 🎯 The Problem This Solves

**Traditional Testing vs LLM Evaluation:**

```python
# ❌ Traditional Unit Test (Brittle for LLMs)
assert response == "Paris"  # Fails if answer is "The capital is Paris"

# ✅ LangSmith Evaluation (Robust)
score = semantic_similarity(response, "Paris")  # Passes if meaning matches
```

**The Architect's Insight**: You can't use `assert` on LLM outputs. You need:
- Semantic similarity scoring
- Trend tracking over time
- Regression detection across deployments

## 📊 What We Built

### 1. Golden Questions Dataset (`evaluation_dataset.json`)
20 curated questions across categories:
- Factual knowledge (CEO of Google, Capital of France)
- Math calculations (Square roots, percentages)
- Science/Technology (Chemical formulas, programming languages)

**Why 20?** Balance between:
- Coverage: Tests diverse reasoning patterns
- Cost: Each question = API call to OpenAI
- Signal: Enough data to detect regressions

### 2. Evaluation Script (`evaluate_agent.py`)

**Key Components:**

```python
# Create LangSmith dataset
evaluator.create_or_update_dataset()

# Run agent against all questions
evaluate(
    agent_wrapper,
    data="golden-questions",
    evaluators=[
        correctness_evaluator,  # Custom: Keyword matching
        LangChainStringEvaluator("embedding_distance")  # Semantic similarity
    ]
)
```

**Evaluation Metrics:**
- **Correctness**: Does answer contain expected value?
- **Embedding Distance**: Semantic similarity (catches paraphrasing)
- **Latency**: Response time tracking (implicit in LangSmith)
- **Tool Usage**: Which tools were called (traced automatically)

### 3. CI/CD Integration (`.github/workflows/ci.yml`)

**Automated on every push to `main`:**

```yaml
evaluate-agent:
  runs-on: ubuntu-latest
  services:
    postgres: # Spins up pgvector for state persistence
  steps:
    - Run evaluation
    - Upload results to LangSmith
    - Comment on PR with dashboard link
```

**Only runs on `main`** to avoid:
- Consuming LangSmith quota on feature branches
- OpenAI API costs on every PR

## 🚀 Usage

### Local Evaluation

```bash
# 1. Set up LangSmith API key
export LANGCHAIN_API_KEY="your-key-from-https://smith.langchain.com/settings"
export LANGCHAIN_TRACING_V2=true
export LANGCHAIN_PROJECT="agent-python"

# 2. Run evaluation
cd agent-python
python evaluate_agent.py
```

**Expected Output:**
```
🎯 Agent Evaluation - Golden Questions Dataset
📚 Loading dataset from evaluation_dataset.json
✅ Dataset ready with 20 questions
🤖 Running agent: What is the CEO of Google?...
✅ Evaluation complete!
📊 View results at: https://smith.langchain.com
```

### CI/CD Evaluation

**Setup GitHub Secrets:**
1. Go to: Repository → Settings → Secrets → Actions
2. Add:
   - `OPENAI_API_KEY`: Your OpenAI key
   - `LANGCHAIN_API_KEY`: Your LangSmith key

**Automatic Run:**
- Every push to `main` triggers evaluation
- Results visible in: Actions → LangSmith Agent Evaluation
- Dashboard link commented on PRs

## 📈 Interpreting Results

### LangSmith Dashboard

**Navigate to**: https://smith.langchain.com → Datasets → `golden-questions`

**Key Views:**

1. **Experiment Comparison**:
   - Compare accuracy across commits
   - Detect regressions (score drops)
   - Track latency trends

2. **Individual Runs**:
   - See exact agent traces
   - Debug failed questions
   - Analyze tool call patterns

3. **Aggregate Metrics**:
   - Average correctness score
   - P95 latency
   - Error rate

### Example Insights

**Good Commit**:
```
Correctness: 18/20 (90%)
Avg Latency: 1.2s
Failed: "What is the main programming language for Android?" 
  → Agent said "Java" instead of "Kotlin" (outdated knowledge)
```

**Regression Detected**:
```
Correctness: 12/20 (60%) ⚠️ DOWN from 90%
  → Code change broke tool calling
  → Agent now hallucinates instead of using search
```

## 🎓 Portfolio Talking Points

### For Interviews

**"Tell me about your approach to testing AI systems"**

> "I implemented a LangSmith evaluation pipeline with 20 'Golden Questions' that runs on every deployment. Unlike traditional unit tests that check exact outputs, I use semantic similarity scoring and trend analysis. For example, if the agent says 'The capital is Paris' vs just 'Paris', the semantic evaluator correctly scores it as correct. This caught a regression where a code change dropped accuracy from 90% to 60% by breaking tool calling."

**Technical Depth**:
- **Dataset Design**: Balanced across factual, math, science (diverse reasoning)
- **Evaluators**: Custom keyword matching + LangChain embedding distance
- **CI/CD Integration**: Only runs on `main` to control costs
- **Observability**: Full trace in LangSmith (tools called, latency, errors)

### Comparison to Alternatives

| Approach | Pros | Cons | When to Use |
|----------|------|------|-------------|
| **Unit Tests** | Fast, deterministic | Brittle for LLMs | Code logic, not LLM outputs |
| **Manual QA** | Catches edge cases | Slow, not scalable | Initial validation |
| **LangSmith Evals** | Robust, tracks trends | Requires API calls | Regression testing, prod monitoring |

## 🔧 Customization

### Adding Questions

Edit `evaluation_dataset.json`:

```json
{
  "question": "What is GDPR?",
  "expected_answer": "General Data Protection Regulation",
  "category": "compliance"
}
```

**Design Tips**:
- Use questions your users actually ask
- Include edge cases (ambiguous queries, multi-step reasoning)
- Balance cost vs coverage (20-50 questions ideal)

### Custom Evaluators

```python
def compliance_evaluator(run: Run, example: Example) -> Dict:
    """Check if answer cites sources (for compliance)."""
    answer = run.outputs.get("answer", "")
    has_citation = "source:" in answer.lower()
    return {
        "key": "has_citation",
        "score": 1.0 if has_citation else 0.0
    }

# Add to evaluation
evaluators=[
    correctness_evaluator,
    compliance_evaluator,  # Your custom logic
]
```

### Advanced: LLM-as-Judge

For complex evaluations, use GPT-4 to score answers:

```python
from langchain.evaluation import load_evaluator

judge = load_evaluator("labeled_criteria", criteria="correctness")

def llm_judge_evaluator(run: Run, example: Example) -> Dict:
    result = judge.evaluate_strings(
        prediction=run.outputs["answer"],
        reference=example.outputs["expected_answer"],
        input=example.inputs["question"]
    )
    return {"key": "llm_judge", "score": result["score"]}
```

## 🎯 Next Steps

**Level Up Your Evaluation**:

1. **Add More Datasets**:
   - Compliance-specific questions (GDPR, SOC2)
   - Multi-turn conversations (test state persistence)
   - Adversarial inputs (test guardrails)

2. **Production Monitoring**:
   - Sample 1% of production queries
   - Run evaluation daily
   - Alert on accuracy drops

3. **A/B Testing**:
   - Create datasets per experiment
   - Compare model versions (GPT-4 vs GPT-4o)
   - Measure cost vs quality tradeoffs

## 📚 Resources

- **LangSmith Docs**: https://docs.smith.langchain.com/evaluation
- **Evaluation Patterns**: https://langchain-ai.github.io/langchain/evaluation/
- **Best Practices**: [LangSmith Evaluation Cookbook](https://github.com/langchain-ai/langsmith-cookbook)

## ⚠️ Important Notes

**Cost Management**:
- Each question = 1 OpenAI API call (~$0.001)
- 20 questions = $0.02 per evaluation
- Running on every commit = ~$0.60/month (30 commits)

**LangSmith Quota**:
- Free tier: 5,000 traces/month
- Running 20 questions = ~20 traces
- Keep under 250 evaluations/month

**Rate Limits**:
- OpenAI: 3 RPM on free tier (evaluation takes ~10 minutes)
- Add delays if hitting limits: `time.sleep(20)`
