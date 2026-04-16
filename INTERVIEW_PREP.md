# Interview Prep — Enterprise RAG Platform

**Topics:** Supervisor-Worker Hierarchy · Time-Travel Checkpointers · HITL Governance  
**Format:** STAR Stories + Architecture Diagrams + Key Metrics

---

## Quick Elevator Pitch (30 seconds)

> "I built a production-grade, compliance-focused RAG platform with a polyglot microservices architecture — Java Spring Boot as the API gateway, a Python LangGraph agent service for stateful multi-turn conversations, and a Next.js frontend with real-time generative UI. The three features I'm most proud of are: a supervisor-worker multi-agent hierarchy for complex research queries, PostgreSQL-backed time-travel checkpointing so conversations survive restarts and can be rewound, and a human-in-the-loop governance layer that interrupts the agent graph before any high-risk tool executes — covering stock trades, email sends, and database deletes — and requires explicit human approval."

---

## STAR Story 1 — Supervisor-Worker Multi-Agent Hierarchy

### The Problem It Solves (Lead with this)

A single LLM call can't simultaneously retrieve current news, pull live stock prices, run quantitative comparisons, and synthesize a coherent report. Asking one model to do everything results in hallucinated numbers, shallow research, or incoherent structure.

---

### S — Situation

> "The platform needed to answer complex enterprise queries like 'Compare AAPL and MSFT's Q4 earnings trends against recent analyst sentiment.' A single LLM call either hallucinated financial data, skipped the research entirely, or produced unformatted output. The root cause was that one model was being asked to be a researcher, a quant analyst, and a writer simultaneously."

### T — Task

> "Design a multi-agent architecture where specialized agents handle distinct concerns, coordinated by a supervisor that routes work intelligently — without adding unnecessary LLM hops or creating a rigid pipeline."

### A — Action

> "I implemented a LangGraph-based Supervisor-Worker pattern in `multi_agent_supervisor.py`. The supervisor is a GPT-4o-mini instance that inspects the incoming query and emits a routing decision — which combination of workers to activate. Three specialized workers exist:
>
> - **Research Agent**: has access to `hybrid_web_search` and `scrape_summary`. It uses Tavily for breaking news and Exa for deep research — routed by pattern matching on the query, so the routing itself costs zero LLM tokens.
> - **Quantitative Agent**: has `get_stock_price` backed by yfinance and pandas. It handles live price data, percentage changes, and numerical comparisons. Separating this from the Research agent means financial numbers are always real, never hallucinated.
> - **Writer Agent**: a pure LLM node with no tools — it only receives the merged outputs of the Research and Quant agents and formats a structured, coherent final report.
>
> The key design decision was separating tool-use agents from the writing agent. If the Writer had access to tools, it might call them redundantly or generate additional LLM costs. By making it downstream-only, it can focus entirely on synthesis quality.
>
> I also wrapped the entire supervisor endpoint with a semantic cache backed by pgvector. Before the supervisor fires, we embed the incoming query and do a cosine similarity search against cached responses. A threshold of 0.92 was chosen deliberately high — in a compliance context, subtly different queries may require substantively different answers."

### R — Result

> "Complex research queries that previously hallucinated stock data now return grounded, cited responses. The separation of concerns reduced per-query hallucination significantly. With semantic caching, repeated or near-identical queries are served in under 10 milliseconds instead of 3–4 seconds, and each cache hit saves approximately $0.03 in OpenAI API costs. The architecture also scales naturally — adding a new specialized agent (e.g., a Regulatory Agent that queries SEC filings) requires zero changes to the supervisor routing logic."

---

### Architecture Diagram — Multi-Agent Supervisor

```
POST /api/multi-agent
{ "query": "Compare AAPL vs MSFT earnings and recent sentiment" }
         │
         ▼
┌─────────────────────────────────────────────────────┐
│              Semantic Cache (pgvector)               │
│  embed(query) ──▶ cosine search ──▶ similarity?     │
│                                                      │
│   ≥ 0.92  ────────────────────────────────────────▶ RETURN cached (< 10ms)
│   < 0.92  ──────────────────────────────────────────────┐
└─────────────────────────────────────────────────────┘   │
                                                           │
                                              ┌────────────▼────────────┐
                                              │     Supervisor Node      │
                                              │      GPT-4o-mini         │
                                              │  "I need Research AND    │
                                              │   Quantitative agents"   │
                                              └──┬──────────┬────────────┘
                                                 │          │
                              ┌──────────────────▼──┐  ┌───▼────────────────┐
                              │    Research Agent    │  │  Quantitative Agent│
                              │                      │  │                    │
                              │  hybrid_web_search() │  │  get_stock_price() │
                              │      │               │  │  yfinance.download │
                              │  ┌───▼───────┐       │  │  pandas analysis   │
                              │  │  Tavily   │       │  │                    │
                              │  │ (news)    │       │  │  Returns:          │
                              │  └───────────┘       │  │  AAPL: $192.45 ▲3% │
                              │  ┌───────────┐       │  │  MSFT: $415.20 ▲1% │
                              │  │    Exa    │       │  └────────────────────┘
                              │  │ (research)│       │
                              │  └───────────┘       │
                              │  Returns:            │
                              │  [analyst articles,  │
                              │   earnings reports]  │
                              └──────────────────────┘
                                          │ merged results
                                          ▼
                              ┌───────────────────────┐
                              │     Writer Agent       │
                              │   (pure LLM, no tools) │
                              │   formats final report │
                              └───────────┬────────────┘
                                          │
                                          ▼
                              ┌───────────────────────┐
                              │   Semantic Cache PUT   │
                              │   (TTL: 300s)          │
                              └───────────┬────────────┘
                                          │
                                          ▼
          {
            "response": "## AAPL vs MSFT Q4 Analysis\n...",
            "agents_used": ["research", "quantitative", "writer"],
            "cache_hit": false,
            "latency_ms": 3420,
            "cost_saved": 0.0
          }
```

### Anticipated Interview Questions

**"Why not just give one agent all the tools?"**
> One agent with many tools tends to call them greedily or miss the right tool for a sub-task. Specialization creates hard separation: the Quant Agent never makes up numbers because it can only call real data APIs. The Writer never calls an API because it has none. This mirrors how real teams work.

**"How does the Supervisor decide routing without another expensive LLM call?"**
> The supervisor is a single GPT-4o-mini call that emits a structured JSON routing decision — which agents to activate. It's not a chain of LLM calls; it's one classification step. And for routing between Tavily and Exa within the Research Agent, I use pattern matching on the query string, which costs zero tokens.

**"What's the 0.92 threshold based on?"**
> It's empirically set to avoid false positives in compliance contexts. At 0.85 you get hits on semantically related but factually different queries — "What is AAPL's price today?" vs "What was AAPL's price last quarter?" At 0.92, those miss the cache and get a fresh LLM response, which is the correct behavior.

---

---

## STAR Story 2 — Time-Travel Checkpointers

### The Problem It Solves (Lead with this)

Stateless agents lose all conversation context on every request. Restarting a container wipes user sessions. Debugging a production failure means you can't reproduce what the agent was "thinking" — all you have is logs.

---

### S — Situation

> "The LangGraph agent service was stateless — each request to `/api/graph` started a fresh conversation. Users lost context between messages, container restarts wiped in-flight sessions, and when an agent produced a wrong or harmful output, there was no way to inspect the exact state that caused it. The lack of durability was a hard blocker for multi-turn compliance workflows."

### T — Task

> "Implement durable state persistence so that: (1) conversations survive container restarts, (2) any past state can be restored and re-evaluated, and (3) users can be isolated from each other in a multi-tenant deployment."

### A — Action

> "I integrated LangGraph's `PostgresSaver` as the checkpointer for the `StateGraph`. Here's precisely what happens:
>
> Every time a LangGraph node completes execution — `call_model`, `call_tool` — the full `AgentState` (a list of `BaseMessage` objects) is serialized to JSONB and written to the `checkpoints` table with a composite key of `(thread_id, checkpoint_id)`. Pending writes that haven't been committed yet go to `checkpoint_writes` to handle partial failures.
>
> For multi-tenancy, every conversation is assigned a UUID `thread_id`. The graph's `configurable` dict is set to `{ 'thread_id': thread_id }`, and the `PostgresSaver` namespaces all checkpoint queries by that ID. No user can access another user's state.
>
> The `/api/rewind` endpoint is the key payoff: given a `thread_id` and a step count `n`, we fetch the checkpoint from `n` steps ago, restore the state, and return the conversation as it existed at that point. This means if an agent made a bad tool call, I can rewind to before that call, inspect the model's reasoning, and understand exactly what went wrong — in production, against real state, without any mock reproduction.
>
> The `checkpoint_writes` table handles the write-ahead buffering. If the service crashes mid-node, the incomplete writes don't corrupt the last committed checkpoint. On restart, LangGraph resumes from the last clean checkpoint transparently."

### R — Result

> "Conversations now survive indefinite container restarts. The time-travel debugging capability has been used to analyze every HITL decision in production — I can rewind to the exact state before a tool call and see the full message history that led the model to propose that action. Multi-tenant isolation is complete: each `thread_id` is a fully independent conversation namespace. The implementation required zero changes to the agent logic — it's purely infrastructure, injected through LangGraph's checkpointer interface."

---

### Architecture Diagram — Time-Travel Checkpointing

```
                                    NORMAL FLOW
                                    ──────────
POST /api/graph { query, thread_id: "abc-123" }
         │
         ▼
┌────────────────────────────────────────────────────────────┐
│                   LangGraph StateGraph                      │
│   config = { configurable: { thread_id: "abc-123" } }      │
│                                                             │
│   ┌─────────────┐  checkpoint_id: "step-1"                 │
│   │ call_model  │ ──────────────────────────────────────┐  │
│   └──────┬──────┘                                       │  │
│          │                                              ▼  │
│   ┌──────▼──────┐  checkpoint_id: "step-2"    ┌─────────────────────┐
│   │ call_tool   │ ──────────────────────────▶ │   PostgresSaver     │
│   └──────┬──────┘                             │                     │
│          │                                    │  checkpoints table: │
│   ┌──────▼──────┐  checkpoint_id: "step-3"    │  (thread_id,        │
│   │ call_model  │ ──────────────────────────▶ │   checkpoint_id,    │
│   └──────┬──────┘                             │   state JSONB)      │
│          │                                    │                     │
│         END                                   │  step-1: [HumanMsg] │
└────────────────────────────────────────────────  step-2: [HumanMsg, │
                                                │   AIMsg(tool_call), │
                                                │   ToolMsg]          │
                                                │  step-3: [all +     │
                                                │   AIMsg(final)]     │
                                                └─────────────────────┘

                                   TIME-TRAVEL
                                   ───────────
POST /api/rewind { thread_id: "abc-123", steps: 2 }
         │
         ▼
  PostgresSaver.get_checkpoint("abc-123", "step-1")
         │
         ▼
  Returns state: { messages: [HumanMsg("buy AAPL")] }
         │         ← before the bad tool call
         ▼
  Agent can be re-invoked from this point
  OR state can be inspected for debugging


                               CRASH RECOVERY
                               ──────────────
Container restart
         │
         ▼
POST /api/graph { query: "...", thread_id: "abc-123" }
         │
         ▼
  PostgresSaver.get_checkpoint("abc-123")
  returns last committed step ──────────────▶ Resume seamlessly
  (checkpoint_writes handles partial writes)
```

### State Schema (What's Persisted)

```
checkpoints table row:
{
  "thread_id":     "abc-123",
  "checkpoint_id": "step-2",
  "checkpoint": {
    "messages": [
      { "type": "human",  "content": "Buy 10 shares of AAPL" },
      { "type": "ai",     "content": "", "tool_calls": [{ "name": "buy_stock", ... }] },
      { "type": "tool",   "content": "Pending human approval", "tool_call_id": "..." }
    ]
  },
  "metadata": { "step": 2, "node": "call_tool" }
}
```

### Anticipated Interview Questions

**"Why PostgreSQL instead of Redis or an in-memory store?"**
> Durability over speed. Redis survives restarts only with persistence enabled, and its JSONB querying for time-travel is awkward. PostgreSQL gives ACID guarantees, native JSONB querying for state inspection, the same pgvector instance we already run, and operational simplicity — one less infrastructure component.

**"How does thread_id prevent cross-tenant data leakage?"**
> The `PostgresSaver` namespaces every SQL query with `WHERE thread_id = $1`. There's no shared state structure — each thread is its own isolated namespace. Even if two users send identical queries, their checkpoints never interact.

**"What's the blast radius of the checkpoint_writes table failing?"**
> Only the current in-flight node's output is at risk. The last committed `checkpoints` row is always clean. On restart, LangGraph reads the last committed checkpoint and re-executes from there. The `checkpoint_writes` table is a write-ahead buffer, not the source of truth.

---

---

## STAR Story 3 — HITL Governance

### The Problem It Solves (Lead with this)

An AI agent with access to financial trading, email sending, or database deletion APIs is a compliance liability without human oversight. Post-hoc review is too late — you can't unsend an email or untrade a stock. Governance must happen before execution.

---

### S — Situation

> "The agent had tools that could execute real-world actions with significant consequences: `buy_stock`, `send_email`, and `delete_database_records`. In a demo context that's impressive. In a compliance context, it's a liability. Regulatory requirements and basic risk management demanded that a human explicitly approve these actions before they execute — not after, not via a log review, but as a hard gate in the execution flow."

### T — Task

> "Build a pre-execution governance layer that: (1) interrupts the agent before any high-risk tool runs, (2) surfaces the tool name and exact inputs to a human reviewer, (3) blocks execution until an explicit approve or reject decision is received, and (4) resumes or aborts the agent graph based on that decision — all while preserving full conversation state across the pause."

### A — Action

> "I used LangGraph's native interrupt mechanism rather than building a custom approval queue. Here's the precise implementation:
>
> In `graph_agent.py`, I defined a `HITL_TOOLS` set: `{ 'buy_stock', 'send_email', 'delete_database_records' }`. Inside the `call_tool` node, before invoking the `ToolExecutor`, the code checks if the requested tool name is in `HITL_TOOLS`. If it is, the node raises a LangGraph `Interrupt`, which halts the graph and saves the full state to PostgreSQL via `PostgresSaver`.
>
> The `/api/graph` endpoint returns immediately with `{ pending_approval: true, tool_name, tool_inputs }`. The frontend renders an approval card — it shows the tool name, all inputs in human-readable form, and a risk level badge. The user sees exactly what the agent wants to do before it happens.
>
> When the user clicks Approve or Reject, the frontend `POST`s to `/api/graph/approve` with `{ thread_id, approve: true/false }`. On approval, the graph resumes from the saved checkpoint and the tool executes. On rejection, a synthetic `ToolMessage` is injected with the content 'Action rejected by human reviewer', and the graph continues to its END node, where the model generates a response explaining the rejection.
>
> The critical design decision: interrupt before the tool node, not inside it. This means the tool's side effects never begin until approval is received. An 'undo' button would require compensating transactions; a 'prevent' button requires interrupting before."

### R — Result

> "Zero high-risk tool executions occur without human approval. The full decision trail — who approved, what tool, what inputs, when — is captured in the audit log. The interrupt-based approach means the agent's reasoning is fully preserved; it doesn't have to 'start over' after an approval, it resumes from the exact checkpoint. The frontend approval card took under a day to build because the state serialization was already handled by the checkpointer. HITL added compliance controls without restructuring any agent logic."

---

### Architecture Diagram — HITL Governance

```
                          HAPPY PATH — SAFE TOOL
                          ───────────────────────
User: "What's AAPL's price?"
         │
         ▼
  call_model ──▶ ToolCall{ name: "get_stock_price", args: {symbol: "AAPL"} }
         │
         ▼
  call_tool ──▶ is "get_stock_price" in HITL_TOOLS?
                         │
                         │  NO
                         ▼
               ToolExecutor.invoke()
                         │
                         ▼
               ToolMessage{ content: "$192.45" }
                         │
                         ▼
               call_model ──▶ "Apple is trading at $192.45"
                         │
                        END


                       HITL PATH — HIGH-RISK TOOL
                       ──────────────────────────
User: "Buy 10 shares of AAPL at market price"
         │
         ▼
  call_model ──▶ ToolCall{ name: "buy_stock",
                            args: { symbol: "AAPL", quantity: 10, price: 192.45 } }
         │
         ▼
  call_tool ──▶ is "buy_stock" in HITL_TOOLS?
                         │
                         │  YES
                         ▼
               ┌─────────────────────────────────────┐
               │         LangGraph INTERRUPT          │
               │                                      │
               │  1. Save full AgentState to          │
               │     PostgreSQL checkpoint            │
               │  2. Return to caller immediately     │
               └─────────────────────────────────────┘
                         │
                         ▼
  POST /api/graph returns:
  {
    "pending_approval": true,
    "tool_name": "buy_stock",
    "tool_inputs": {
      "symbol": "AAPL",
      "quantity": 10,
      "price": 192.45
    }
  }
                         │
                         ▼
  ┌───────────────────────────────────────────────────┐
  │              Frontend Approval Card                │
  │                                                    │
  │   ⚠ HIGH RISK ACTION REQUIRES APPROVAL            │
  │                                                    │
  │   Tool:     buy_stock                              │
  │   Symbol:   AAPL                                   │
  │   Quantity: 10 shares                              │
  │   Price:    $192.45                                │
  │   Total:    ~$1,924.50                             │
  │                                                    │
  │   [  APPROVE  ]          [  REJECT  ]              │
  └───────────────────────────────────────────────────┘
         │                          │
         │ APPROVE                  │ REJECT
         ▼                          ▼
  POST /api/graph/approve    POST /api/graph/approve
  { approve: true }          { approve: false }
         │                          │
         ▼                          ▼
  Restore checkpoint         Inject ToolMessage:
  Resume graph               { content: "Action rejected
  ToolExecutor.invoke()        by human reviewer" }
         │                          │
         ▼                          ▼
  "Trade executed:           call_model:
   10 AAPL @ $192.45"        "I was unable to proceed
                              with the trade as it was
                              rejected by your reviewer."


                        TOOL RISK CLASSIFICATION
                        ────────────────────────

  ┌────────────────────────────┬────────────┬──────────────────────┐
  │ Tool                       │ Risk Level │ Interrupt Required   │
  ├────────────────────────────┼────────────┼──────────────────────┤
  │ hybrid_web_search          │ Safe       │ No                   │
  │ get_stock_price            │ Safe       │ No                   │
  │ scrape_summary             │ Safe       │ No                   │
  │ buy_stock                  │ HIGH       │ YES                  │
  │ send_email                 │ HIGH       │ YES                  │
  │ delete_database_records    │ CRITICAL   │ YES                  │
  └────────────────────────────┴────────────┴──────────────────────┘
```

### Anticipated Interview Questions

**"Why interrupt before the tool node rather than inside the tool itself?"**
> If you gate inside the tool function, the function has already been invoked — its preamble code may have run. More importantly, placing the gate in the LangGraph node means the approval logic lives at the orchestration level, not scattered across every tool implementation. New tools automatically get HITL by adding their name to one set.

**"What happens to state during the approval wait time?"**
> It's fully durable in PostgreSQL. The approval wait could be seconds or days — the state doesn't expire. When the user approves at 2am, the graph resumes from the exact checkpoint as if no time passed. This is a direct payoff of the time-travel checkpointing system.

**"How do you prevent a malicious user from calling `/api/graph/approve` for someone else's session?"**
> The `thread_id` is the isolation boundary. In production this maps to an authenticated user session — the Java gateway validates the JWT and only passes the user's own `thread_id` to the Python service. The Python service itself treats it as an opaque tenant key.

**"What if the user closes the browser before approving?"**
> State persists. On next login, the frontend can `GET /api/graph/pending?thread_id=...` to check if any approval is outstanding and re-render the approval card. The graph remains paused indefinitely until a decision is made.

---

---

## Combined Architecture Diagram — All Three Systems

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         Next.js Frontend                                 │
│                                                                          │
│  ┌────────────────────────────────────┐  ┌────────────────────────────┐ │
│  │         ChatInterface              │  │        HITLChat             │ │
│  │   (SSE streaming, artifact render) │  │  (Approval cards, Approve/ │ │
│  │   └─▶ ArtifactComponents          │  │   Reject buttons, badges)   │ │
│  │       (Recharts, DataTable, Cards) │  └────────────┬───────────────┘ │
│  └────────────────────────────────────┘               │                 │
└──────────────────────────────────────┬────────────────┘─────────────────┘
                                       │ REST / SSE
                         ┌─────────────▼──────────────────┐
                         │     Java Spring Boot :8080      │
                         │                                 │
                         │  JWT Auth  ──  PII AOP          │
                         │  ChatService ── IngestionSvc    │
                         │  AuditLog  ── Circuit Breaker   │
                         └──────┬──────────────────────────┘
                                │ HTTP (Resilience4j CB)
          ┌─────────────────────▼──────────────────────────────────────┐
          │               Python FastAPI Agent :8000                    │
          │                                                             │
          │  ┌──────────────────────────────────────────────────────┐  │
          │  │            LangGraph StateGraph                       │  │
          │  │                                                       │  │
          │  │   call_model ──▶ HITL check ──▶ call_tool            │  │
          │  │       │              │               │                │  │
          │  │       │         INTERRUPT ◀──── HITL_TOOLS?          │  │
          │  │       │         (save state)    (buy_stock,           │  │
          │  │       │              │           send_email,          │  │
          │  │       │         await human      delete_db)           │  │
          │  │       │         approval                              │  │
          │  │       │              │                                │  │
          │  │       └──────────────┘                                │  │
          │  └──────────────────────────────────────────────────────┘  │
          │                                                             │
          │  ┌──────────────────────────────────────────────────────┐  │
          │  │          Multi-Agent Supervisor                       │  │
          │  │                                                       │  │
          │  │  SemanticCache.get() ──▶ HIT → return (< 10ms)      │  │
          │  │       │ MISS                                          │  │
          │  │  Supervisor ──▶ Research │ Quantitative │ Writer     │  │
          │  │  (routing)      (Tavily/ │ (yfinance/   │ (format)   │  │
          │  │                  Exa)    │  pandas)     │            │  │
          │  │                         │              │             │  │
          │  │  SemanticCache.put() ◀──┴──────────────┘            │  │
          │  └──────────────────────────────────────────────────────┘  │
          └─────────────────────────────────────────────────────────────┘
                                │ SQL + pgvector
          ┌─────────────────────▼──────────────────────────────────────┐
          │               PostgreSQL 16 + pgvector                     │
          │                                                             │
          │  vector_store    ← Document embeddings (HNSW, 1536d)       │
          │  checkpoints     ← LangGraph state snapshots (JSONB)       │
          │  checkpoint_writes ← Write-ahead buffer                    │
          │  semantic_cache  ← Query-response cache (IVFFlat, 1536d)   │
          │  chat_audit_logs ← Compliance audit trail                  │
          │  users           ← JWT auth                                │
          └─────────────────────────────────────────────────────────────┘

   LEGEND:
   ──▶  Synchronous call
   ◀──  Response / callback
   ═══  Persistence boundary
```

---

## Key Metrics to Cite

### Performance

| Metric | Value | Context |
|---|---|---|
| Semantic cache hit latency | < 10 ms | vs ~2,000 ms LLM call — 200× faster |
| Semantic cache similarity threshold | 0.92 cosine | High precision; compliance-safe |
| Cache TTL | 300 seconds | Balance freshness vs cost |
| Cost saved per cache hit | ~$0.03 | Skips full LLM pipeline |
| Vector dimensions | 1,536 | OpenAI text-embedding-3-small |
| RAG chunk size | 800 tokens | 400-token overlap for continuity |
| RAG top-k | 3 chunks | Precision over recall; avoids context dilution |
| LLM temperature (RAG) | 0.3 | Deterministic compliance answers |
| LLM temperature (agents) | 0.0 | Structured tool-calling output |
| JWT expiry | 24 hours | Session security vs UX tradeoff |

### Architecture Scale Numbers

| Dimension | Value |
|---|---|
| Total services | 6 (frontend, Java, Python, Postgres, Prometheus, Grafana) |
| HITL tool categories | 3 (financial, communication, data destruction) |
| Specialized sub-agents | 3 (Research, Quantitative, Writer) |
| Search engines integrated | 2 (Tavily + Exa) with automatic fallback |
| CI/CD workflows | 4 (test, deploy-aws, red-team, docker-build) |
| Vector index types | 2 (HNSW for RAG, IVFFlat for cache) |
| PostgreSQL tables | 6 (vector_store, users, audit_logs, checkpoints, checkpoint_writes, semantic_cache) |

### Reliability

| Mechanism | Behavior |
|---|---|
| Resilience4j circuit breaker | Opens at 50% failures over 10-request window; 5s wait before half-open |
| Hybrid search fallback | If Tavily fails → Exa automatically; if Exa fails → Tavily |
| Checkpoint durability | Conversations survive container restarts via PostgreSQL ACID writes |
| HITL state durability | Approval can be completed seconds or days after interrupt — state never expires |

---

## Talking Points by Interviewer Type

### Engineering Manager / Principal Engineer

> Lead with the governance angle: "The HITL system is a pre-execution compliance gate, not a post-hoc review. The distinction matters in regulated industries — by the time you review a log, the trade has already happened. The interrupt fires before any side effects begin."

### Staff / Senior Engineer (Technical Depth)

> Go deep on the LangGraph internals: "The checkpoint is written after every node, not just at conversation end. This means you can reconstruct not just the final answer but every intermediate reasoning step — every tool call, every model output. That's what makes time-travel debugging possible rather than just conversation replay."

### System Design Interview

> Emphasize the polyglot tradeoff: "I deliberately chose two languages. Java owns the gateway — JWT security, Spring AOP for PII sanitization, JPA for compliance audit logs, and the Spring AI RAG pipeline. Python owns the AI layer — LangGraph has no Java equivalent, and the ecosystem for LangChain, yfinance, and SSE streaming is native Python. The Resilience4j circuit breaker between them means a Python OOM crash degrades gracefully to standard RAG rather than taking down the entire platform."

### Behavioral / STAR-heavy Interview

> Use the HITL story for "tell me about a time you solved a complex problem": the situation is a clear compliance risk, the task has a hard constraint (pre-execution, not post), the action has a specific technical decision (LangGraph interrupt vs custom queue), and the result is measurable (zero unauthorized high-risk executions).

---

*End of Interview Prep*
