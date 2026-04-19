# Claude Agent SDK Migration Design Document

**Enterprise RAG Platform — Agentic Workflow Redesign**
**Date:** 2026-04-18
**Status:** Proposal

---

## 1. Executive Summary

The current platform uses LangGraph (Python) orchestrated via FastAPI for all agentic workflows — stateful graph execution, HITL approvals, multi-agent supervision, and semantic caching. This document proposes a redesign using the **Claude Agent SDK**, evaluating how its native primitives — tools, hooks, skills, and the agent loop — map to our existing patterns, and where it delivers meaningful improvements.

---

## 2. Current Architecture Overview

```
Frontend (Next.js)
      │  HTTP / SSE
      ▼
Java API Gateway (Spring Boot :8080)
      │  REST (circuit-breaker)
      ▼
Python Agent Engine (FastAPI :8000)
  ├── LangGraph StateGraph (graph_agent.py)
  │     ├── call_model node   ← GPT-4o-mini + bound tools
  │     ├── call_tool node    ← ToolExecutor
  │     └── PostgresSaver     ← checkpoint persistence
  ├── Multi-Agent Supervisor (multi_agent_supervisor.py)
  │     ├── Research Agent    ← DuckDuckGo + scraper
  │     ├── Quantitative Agent← yfinance + pandas
  │     └── Writer Agent      ← pure LLM
  ├── Hybrid Search (hybrid_search.py)
  │     ├── Tavily            ← recency queries
  │     └── Exa               ← depth/research queries
  ├── Semantic Cache (semantic_cache.py)
  │     └── pgvector IVFFlat  ← similarity threshold 0.92
  └── Generative UI (generative_ui.py)
        └── SSE artifact streaming
```

**Key pain points in the current design:**

| Area | Problem |
|------|---------|
| HITL | `interrupt_before=["action"]` is a graph-level hack — it pauses the entire graph, not a specific tool invocation |
| Multi-agent | Manual state routing via `next_agent` field; supervisor logic is bespoke Python |
| Tool safety | HITL tools identified by name string matching (`HITL_TOOLS = [...]`) — fragile |
| Observability | No first-class tracing; hooks are Java AOP only, not in the agent loop |
| Model lock-in | Hard-coded to OpenAI `gpt-4o-mini` / `gpt-4-turbo` throughout |
| Streaming | SSE protocol hand-rolled in `generative_ui.py` |

---

## 3. Claude Agent SDK Primitives

### 3.1 Tools

In the Claude Agent SDK, tools are defined as typed, named callables that Claude invokes during its reasoning loop. They map directly to our existing `@tool` functions but gain:

- **Input schema validation** (JSON Schema, auto-generated from Python type hints)
- **First-class error handling** — tool errors surface as structured `tool_result` blocks, not exceptions
- **Parallel tool calls** — Claude 4.x can invoke multiple tools concurrently within one turn

**Current:**
```python
# graph_agent.py
@tool
def hybrid_web_search(query: str) -> str:
    """Routes between Tavily (recency) and Exa (depth)"""
    return run_hybrid_search(query)

tools = [hybrid_web_search, buy_stock, send_email, delete_database_records]
tool_executor = ToolExecutor(tools)
model = model.bind_tools(tools)
```

**Claude Agent SDK equivalent:**
```python
# tools/search.py
import anthropic

client = anthropic.Anthropic()

tools = [
    {
        "name": "hybrid_web_search",
        "description": "Routes between Tavily (recency) and Exa (depth) based on query type",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "The search query"}
            },
            "required": ["query"]
        }
    },
    {
        "name": "buy_stock",
        "description": "Purchase stock — REQUIRES human approval before execution",
        "input_schema": {
            "type": "object",
            "properties": {
                "symbol":   {"type": "string"},
                "quantity": {"type": "integer"},
                "price":    {"type": "number"}
            },
            "required": ["symbol", "quantity", "price"]
        }
    }
]
```

### 3.2 The Agent Loop

The SDK's `client.messages.create()` with `tools` replaces LangGraph's `StateGraph`. The agent loop is explicit and testable:

```python
# agent_loop.py
def run_agent(query: str, thread_id: str) -> str:
    messages = load_history(thread_id)  # from postgres
    messages.append({"role": "user", "content": query})

    while True:
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=4096,
            tools=tools,
            messages=messages
        )

        messages.append({"role": "assistant", "content": response.content})

        if response.stop_reason == "end_turn":
            save_history(thread_id, messages)
            return extract_text(response)

        # Process tool calls
        tool_results = []
        for block in response.content:
            if block.type == "tool_use":
                result = dispatch_tool(block.name, block.input)
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": result
                })

        messages.append({"role": "user", "content": tool_results})
```

This is functionally identical to LangGraph's `call_model → call_tool` loop but without the graph compilation overhead, and it's directly inspectable.

### 3.3 Hooks

Claude Agent SDK hooks intercept points in the agent lifecycle. They are the SDK's answer to our Java `@SanitizePii` AOP and LangGraph's `interrupt_before`.

**Available hook points:**

| Hook | Fires When | Our Use Case |
|------|-----------|-------------|
| `pre_tool_call` | Before any tool invocation | PII sanitization, HITL gating, audit logging |
| `post_tool_call` | After tool returns | Result sanitization, cost tracking |
| `pre_model_call` | Before LLM invocation | Prompt injection, caching check |
| `post_model_call` | After LLM responds | Response filtering, audit trail |
| `on_error` | On any exception | Alerting, graceful degradation |

**HITL via hook (replaces `interrupt_before=["action"]`):**
```python
# hooks/hitl_hook.py
HITL_TOOLS = {"buy_stock", "send_email", "delete_database_records"}

async def pre_tool_call_hook(tool_name: str, tool_input: dict, ctx: HookContext):
    if tool_name not in HITL_TOOLS:
        return  # allow

    # Persist pending approval
    approval_id = await store_pending_approval(
        thread_id=ctx.thread_id,
        tool_name=tool_name,
        tool_input=tool_input
    )

    # Block until human decision
    decision = await wait_for_approval(approval_id, timeout=300)

    if not decision.approved:
        raise ToolDeniedError(f"Human rejected {tool_name}: {decision.reason}")
    # If approved, hook returns normally and tool executes
```

This is cleaner than LangGraph's `interrupt_before` because:
- It interrupts at the **specific tool**, not the entire graph
- The approval check is co-located with the tool gate logic
- Rejection raises a structured exception, not a silent state mutation

**PII sanitization hook (replaces Java AOP):**
```python
# hooks/pii_hook.py
import re

PII_PATTERNS = {
    "EMAIL": re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,6}"),
    "PHONE": re.compile(r"\d{3}[-.]?\d{3}[-.]?\d{4}"),
    "SSN":   re.compile(r"\d{3}-\d{2}-\d{4}"),
}

def pre_model_call_hook(messages: list, ctx: HookContext):
    for msg in messages:
        if isinstance(msg.get("content"), str):
            for label, pattern in PII_PATTERNS.items():
                msg["content"] = pattern.sub(f"[REDACTED {label}]", msg["content"])
    return messages
```

Moving PII sanitization into the SDK hook layer means it applies to **all model calls** — including multi-agent sub-calls — without needing Java AOP instrumentation.

### 3.4 Skills

Skills in the Claude Agent SDK are reusable, composable agent capabilities. They are higher-order than tools — a skill encapsulates a complete reasoning pattern, often combining multiple tools with orchestration logic.

**Mapping to our multi-agent supervisor:**

```
Current: MultiAgentSupervisor
  └── manually routes to Research/Quantitative/Writer sub-agents
      via next_agent field in shared TypedDict state

Proposed: Skills
  ├── research_skill     ← web search + scraping + synthesis
  ├── quantitative_skill ← yfinance + pandas analysis
  └── report_skill       ← structured formatting
```

**Skill definition:**
```python
# skills/research_skill.py
from anthropic import Anthropic

client = Anthropic()

RESEARCH_TOOLS = [hybrid_web_search_tool, scrape_summary_tool]

def research_skill(topic: str, depth: str = "standard") -> str:
    """
    Researches a topic using web search and scraping.
    Returns structured findings as markdown.
    """
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=2048,
        system="You are a research specialist. Find accurate, sourced information.",
        tools=RESEARCH_TOOLS,
        messages=[{"role": "user", "content": f"Research: {topic}. Depth: {depth}"}]
    )
    return extract_final_text(response)
```

**Composing skills into a supervisor:**
```python
# supervisor.py
def run_supervisor(query: str) -> SupervisorResult:
    plan = plan_task(query)  # LLM determines which skills are needed

    results = {}
    if plan.needs_research:
        results["research"] = research_skill(plan.research_topic)
    if plan.needs_quantitative:
        results["quant"] = quantitative_skill(plan.symbols, plan.period)

    final = report_skill(query, results)
    return SupervisorResult(answer=final, skills_used=list(results.keys()))
```

Compared to the current `MultiAgentState` with manual `next_agent` routing, skills are:
- **Independently testable** — each skill is a pure function
- **Reusable across agents** — `research_skill` can be called from the graph agent or the supervisor
- **No shared mutable state** — results passed explicitly, not via TypedDict mutations

---

## 4. Feature-by-Feature Migration Plan

### 4.1 Stateful Graph Agent → SDK Agent Loop + PostgreSQL History

| Aspect | Current (LangGraph) | Claude Agent SDK |
|--------|--------------------|--------------------|
| State management | `PostgresSaver` checkpoints per node | Messages array persisted per turn |
| Time-travel | `rewind` via checkpoint_id | Re-run from any message index |
| Thread isolation | `thread_id` config key | `thread_id` in persistence layer |
| Compiled graph | `workflow.compile()` required | No compilation step |
| Conditional routing | `should_continue` edge function | `stop_reason == "end_turn"` check |

**New endpoint:**
```python
# main.py
@app.post("/api/agent")
async def run_agent_endpoint(req: AgentRequest):
    history = await load_thread(req.thread_id)
    result = await run_agent_with_hooks(
        query=req.query,
        history=history,
        hooks=[pii_hook, hitl_hook, audit_hook],
        thread_id=req.thread_id
    )
    await save_thread(req.thread_id, result.updated_history)
    return AgentResponse(
        answer=result.text,
        pending_approval=result.pending_approval,
        approval_id=result.approval_id
    )
```

### 4.2 HITL → `pre_tool_call` Hook

| Aspect | Current (LangGraph) | Claude Agent SDK |
|--------|--------------------|--------------------|
| Interrupt mechanism | `interrupt_before=["action"]` — graph-wide pause | `pre_tool_call` hook — per-tool gate |
| Tool identification | String list `HITL_TOOLS` | Hook checks `tool_name` |
| State at interrupt | Entire graph state frozen in PostgreSQL | Just the pending `tool_use` block |
| Resume mechanism | `run_graph_agent(None)` re-invocation | Hook awaits approval then returns |
| Rejection handling | Inject `HumanMessage("Approval denied")` | Raise `ToolDeniedError` |
| Frontend polling | `POST /api/graph/pending` per thread | `GET /api/approvals/{approval_id}` |

**Frontend change** — instead of polling for graph interrupt state, the API immediately returns an `approval_id`:

```typescript
// HITLChat.tsx — simplified
const res = await fetch('/api/agent', { method: 'POST', body: JSON.stringify({ query }) })
const data = await res.json()

if (data.pending_approval) {
  setApprovalId(data.approval_id)   // show approval card
} else {
  addMessage(data.answer)
}

// User clicks Approve
await fetch(`/api/approvals/${approvalId}/decide`, {
  method: 'POST',
  body: JSON.stringify({ approved: true })
})
// Long-poll or WebSocket for final answer
```

### 4.3 Multi-Agent Supervisor → Skills + Parallel Tool Calls

| Aspect | Current | Claude Agent SDK |
|--------|---------|-----------------|
| Agent definition | LangGraph nodes with TypedDict state | Skill functions with explicit I/O |
| Routing | Supervisor LLM sets `next_agent` field | Supervisor LLM calls skill-tools in parallel |
| Communication | Shared `MultiAgentState` mutations | Return values passed as tool results |
| Parallelism | Sequential node execution | Native parallel `tool_use` blocks |
| Testability | Requires full graph compilation | Direct function calls |

**Parallel skill invocation using Claude 4.x tool parallelism:**

```python
# When Claude returns multiple tool_use blocks in one response,
# they can be executed concurrently

tool_results = await asyncio.gather(*[
    dispatch_tool(block.name, block.input)
    for block in response.content
    if block.type == "tool_use"
])
```

For a query like "Compare AAPL and MSFT earnings and write a report," Claude would emit:
```
tool_use: research_skill(topic="AAPL earnings Q1 2026")
tool_use: research_skill(topic="MSFT earnings Q1 2026")
tool_use: quantitative_skill(symbols=["AAPL", "MSFT"])
```
All three run in parallel, then results feed into `report_skill`.

### 4.4 Semantic Cache → `pre_model_call` Hook

| Aspect | Current | Claude Agent SDK |
|--------|---------|-----------------|
| Cache check | Manual lookup before agent invocation | `pre_model_call` hook intercepts automatically |
| Cache key | pgvector cosine similarity on query embedding | Same — hook calls existing SemanticCache |
| Short-circuit | Separate `if cache_hit: return cached` branch | Hook returns early, skips LLM call entirely |
| Stats tracking | Inline counters in `SemanticCache` | Hook updates stats on every intercept |

```python
# hooks/cache_hook.py
async def pre_model_call_hook(messages: list, ctx: HookContext):
    last_user_msg = get_last_user_message(messages)
    hit = await semantic_cache.lookup(last_user_msg)
    if hit:
        ctx.short_circuit(hit.response)  # skip LLM, return cached response
        await semantic_cache.record_hit(hit.id)
```

### 4.5 PII Protection → Unified Hook (replaces Java AOP)

Currently, PII sanitization lives in Java (`PiiSanitizationAspect`) and is applied only to requests that flow through the Java gateway. Sub-agent calls within LangGraph bypass it entirely.

With SDK hooks, PII sanitization applies at the model call boundary — **every** LLM invocation, including skill sub-calls:

```python
# hooks/pii_hook.py
def pre_model_call_hook(messages, ctx):
    return sanitize_all_messages(messages)  # applied universally

def post_tool_call_hook(tool_name, result, ctx):
    return sanitize_text(result)  # also sanitize tool outputs
```

### 4.6 Hybrid Search → Unchanged Tool

The hybrid search logic (`hybrid_search.py`) requires no changes — the routing heuristic, Tavily/Exa fallback, and return format map directly to an SDK tool definition.

```python
{
    "name": "hybrid_web_search",
    "description": "Pattern-routes to Tavily (recency) or Exa (depth). Auto-fallbacks.",
    "input_schema": {
        "type": "object",
        "properties": {"query": {"type": "string"}},
        "required": ["query"]
    }
}

def execute_hybrid_web_search(query: str) -> str:
    return hybrid_search.run(query)  # existing implementation unchanged
```

### 4.7 Generative UI Streaming → SDK Streaming API

The current SSE streaming in `generative_ui.py` is hand-rolled. The Claude Agent SDK has native streaming support:

```python
# generative_ui_sdk.py
@app.post("/api/generative-ui")
async def generative_ui_stream(req: UIRequest):
    async def event_stream():
        async with client.messages.stream(
            model="claude-sonnet-4-6",
            max_tokens=4096,
            tools=ALL_TOOLS,
            messages=[{"role": "user", "content": req.query}]
        ) as stream:
            async for event in stream:
                if event.type == "content_block_start":
                    yield f"data: {json.dumps({'type': 'status', 'message': 'Thinking...'})}\n\n"
                elif event.type == "tool_use":
                    artifact = await generate_artifact(event.name, event.input)
                    yield f"data: {json.dumps({'type': 'artifact', 'artifact': artifact})}\n\n"
                elif event.type == "message_stop":
                    yield f"data: {json.dumps({'type': 'done'})}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")
```

---

## 5. Proposed Architecture

```
Frontend (Next.js)
      │  HTTP / SSE / WebSocket
      ▼
Java API Gateway (Spring Boot :8080)
  └── Thin pass-through — auth, audit logging, PII check at gateway
      │  REST
      ▼
Python Claude Agent Engine (FastAPI :8000)
  ├── Agent Loop (agent_loop.py)
  │     ├── claude-sonnet-4-6 via Anthropic SDK
  │     ├── Parallel tool execution
  │     └── PostgreSQL message history
  │
  ├── Hooks Pipeline (hooks/)
  │     ├── pre_model_call:  cache_hook → pii_hook
  │     ├── pre_tool_call:   hitl_hook → audit_hook
  │     ├── post_tool_call:  pii_hook (result) → cost_hook
  │     └── post_model_call: audit_hook
  │
  ├── Tools (tools/)
  │     ├── hybrid_web_search   ← Tavily + Exa (unchanged)
  │     ├── buy_stock           ← gated by hitl_hook
  │     ├── send_email          ← gated by hitl_hook
  │     └── delete_db_records   ← gated by hitl_hook
  │
  ├── Skills (skills/)
  │     ├── research_skill      ← search + scrape + synthesize
  │     ├── quantitative_skill  ← yfinance + pandas
  │     └── report_skill        ← formatting + narrative
  │
  ├── Semantic Cache (semantic_cache.py — unchanged)
  │     └── pgvector IVFFlat, threshold 0.92
  │
  └── Generative UI (generative_ui_sdk.py)
        └── Native SDK streaming
```

---

## 6. Comparison: LangGraph vs Claude Agent SDK

### 6.1 Feature Comparison Matrix

| Feature | LangGraph (Current) | Claude Agent SDK | Winner |
|---------|-------------------|-----------------|--------|
| **Agent loop** | `StateGraph` compile + node routing | Explicit `while stop_reason != "end_turn"` loop | SDK — simpler, debuggable |
| **HITL** | `interrupt_before=["action"]` graph pause | `pre_tool_call` hook with awaitable approval | SDK — scoped to tool, not entire graph |
| **Tool definition** | `@tool` decorator + LangChain ToolExecutor | JSON schema dict + dispatcher function | Tie — both clean |
| **Parallel tool calls** | Sequential node execution | Native parallel `tool_use` blocks | SDK — built-in concurrency |
| **Multi-agent** | Manual `next_agent` TypedDict routing | Skills as composable function calls | SDK — cleaner composition |
| **Streaming** | Hand-rolled SSE in FastAPI | Native `client.messages.stream()` | SDK — less boilerplate |
| **State persistence** | PostgresSaver (node-level checkpoints) | Custom message history in PostgreSQL | LangGraph — more granular checkpoints |
| **Time-travel debug** | Built-in `rewind` via checkpoint_id | Manual message-index replay | LangGraph — better out-of-box |
| **PII protection** | Java AOP only (misses sub-agent calls) | `pre_model_call` hook covers all LLM calls | SDK — comprehensive |
| **Semantic caching** | Manual `if cache_hit` branch | `pre_model_call` hook intercept | SDK — automatic, transparent |
| **Model switching** | Hard-coded `gpt-4o-mini` | Config-driven, any Claude model | SDK — flexibility |
| **Observability** | Prometheus metrics only | Hook-based tracing at every lifecycle point | SDK — richer |
| **Vendor lock-in** | OpenAI + LangGraph | Anthropic + Claude | Tie — different vendors |
| **Learning curve** | High — graph compilation, edge functions | Low — standard Python async patterns | SDK — shallower |
| **Ecosystem maturity** | Mature, production-proven | Growing, newer | LangGraph — more battle-tested |
| **Testing** | Requires graph compilation | Pure functions, no compilation | SDK — easier unit testing |

### 6.2 Code Complexity Comparison

**HITL approval flow — lines of code:**

| Layer | LangGraph | Claude Agent SDK |
|-------|----------|-----------------|
| Graph interrupt setup | 8 lines (compile with interrupt_before) | 0 lines (handled in hook) |
| `check_pending_approval()` | 25 lines | 5 lines (query approvals table) |
| `approve_and_continue()` | 30 lines (state mutation + resume) | 10 lines (update row, unblock hook) |
| Frontend polling logic | 40 lines (polling loop + state) | 15 lines (direct approval_id fetch) |
| **Total** | **~103 lines** | **~30 lines** |

**Multi-agent supervisor — setup overhead:**

| Layer | LangGraph | Claude Agent SDK |
|-------|----------|-----------------|
| State TypedDict | 15 lines | 0 — skills have explicit returns |
| Node functions | 60 lines (3 agents × 20 lines) | 60 lines (3 skills × 20 lines) |
| Graph wiring | 25 lines (add_node, add_edge, compile) | 0 — supervisor LLM routes natively |
| Routing logic | 20 lines (conditional edges) | 0 — parallel tool calls handle it |
| **Total** | **~120 lines** | **~60 lines** |

### 6.3 Operational Comparison

| Concern | LangGraph | Claude Agent SDK |
|---------|----------|-----------------|
| **Startup cost** | Graph compilation on every deploy | None |
| **Memory footprint** | Full state graph in memory per thread | Messages array only |
| **Database load** | Writes checkpoint per graph node | Writes once per turn |
| **Error recovery** | Resume from last checkpoint node | Re-run from last saved message |
| **Cost per query** | OpenAI pricing (gpt-4o-mini) | Anthropic pricing (Sonnet 4.6) |
| **Prompt caching** | Not supported | Built-in — system prompts cached |
| **Rate limits** | OpenAI limits | Anthropic limits |

### 6.4 When to Keep LangGraph

The Claude Agent SDK does not fully replace LangGraph in every scenario. Keep LangGraph when:

1. **Fine-grained checkpoint replay** — LangGraph's node-level checkpoints allow replaying from mid-graph. The SDK's message-history approach only replays from turn boundaries. If time-travel debugging at the node level is critical, LangGraph has an edge.

2. **Complex conditional branching** — If the workflow has more than 5 conditional routing paths, LangGraph's visual graph model is easier to reason about than a deeply nested `if/elif` dispatcher.

3. **OpenAI model requirement** — If GPT-4o or other OpenAI models are required (e.g., for compliance with existing vendor agreements), LangGraph's model-agnostic design is an advantage.

4. **Existing investment** — The current LangGraph implementation is functional and well-understood by the team. Migration has real cost.

---

## 7. Implementation Roadmap

### Phase 1: Foundation (Week 1–2)
- [ ] Add `anthropic` SDK dependency alongside existing LangChain deps
- [ ] Implement base `agent_loop.py` with message history persistence
- [ ] Port `hybrid_web_search` tool to SDK tool format (JSON schema)
- [ ] Implement `pii_hook` as `pre_model_call` hook
- [ ] Wire `semantic_cache` into `pre_model_call` hook
- [ ] Shadow-run SDK agent alongside LangGraph for the same queries, compare outputs

### Phase 2: HITL Migration (Week 3)
- [ ] Implement `hitl_hook` as `pre_tool_call` hook
- [ ] Add `approvals` table to PostgreSQL
- [ ] Create `/api/approvals/{id}/decide` endpoint
- [ ] Update `HITLChat.tsx` to use `approval_id` flow (remove polling loop)
- [ ] Migrate `buy_stock`, `send_email`, `delete_db_records` tools
- [ ] End-to-end HITL test: approve + reject paths

### Phase 3: Skills + Multi-Agent (Week 4)
- [ ] Extract `research_skill` from current Research Agent node
- [ ] Extract `quantitative_skill` from Quantitative Agent node
- [ ] Extract `report_skill` from Writer Agent node
- [ ] Implement parallel skill dispatch in supervisor
- [ ] Replace `multi_agent_supervisor.py` supervisor with SDK supervisor
- [ ] Validate output parity with current multi-agent results

### Phase 4: Streaming + Cleanup (Week 5)
- [ ] Replace hand-rolled SSE in `generative_ui.py` with SDK streaming
- [ ] Add `post_model_call` audit hook (replaces Java AOP for agent responses)
- [ ] Remove LangGraph dependency (or keep as optional fallback)
- [ ] Update observability: hook-based traces → Prometheus metrics

### Phase 5: Validation (Week 6)
- [ ] Load test both implementations under 50 concurrent users
- [ ] Compare cache hit rates, HITL latency, multi-agent accuracy
- [ ] Full security review: PII coverage, HITL bypass attempts
- [ ] Documentation update + team knowledge transfer

---

## 8. Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|-----------|
| Claude model quality differs from GPT-4o-mini | Medium | Medium | Shadow-run Phase 1 with A/B evaluation |
| HITL hook timeout in production | Low | High | Configurable timeout + fallback to rejection |
| Anthropic rate limits at 50 concurrent users | Medium | High | Implement prompt caching + request queuing |
| Loss of node-level checkpoint granularity | High | Low | Keep checkpoint table, write per-turn instead of per-node |
| Skills not replicating multi-agent reasoning quality | Medium | Medium | Evaluate on 100 representative queries before cutover |
| Java AOP PII checks become redundant | Low | Low | Keep as defense-in-depth; SDK hooks are primary |

---

## 9. Cost Analysis

### Current (OpenAI)
- GPT-4o-mini input: $0.15 / 1M tokens
- GPT-4-turbo input: $10.00 / 1M tokens (RAG path)
- Embeddings: $0.02 / 1M tokens

### Proposed (Claude + Prompt Caching)
- Claude Sonnet 4.6 input: $3.00 / 1M tokens
- Claude Sonnet 4.6 cached input: $0.30 / 1M tokens (90% discount)
- Embeddings: unchanged (OpenAI text-embedding-3-small)

**With prompt caching enabled on system prompts and tool definitions:**

For typical agent queries (system prompt = ~2K tokens, re-used across turns):
- LangGraph (no caching): 2K system tokens × $0.15 = $0.0003 per call
- SDK with caching: 2K cached tokens × $0.30/1M = $0.000006 per call after first

The semantic cache (0.92 threshold, currently saving ~$0.03/hit) compounds with Claude's prompt caching to further reduce cost.

---

## 10. Decision Recommendation

**Proceed with migration to Claude Agent SDK**, subject to Phase 1 shadow-run validation confirming output quality parity.

The primary gains are:
1. **Simpler HITL** — per-tool hook replaces graph-level interrupt state machine
2. **Unified PII coverage** — hooks cover sub-agent calls that Java AOP misses today
3. **Parallel multi-agent** — native tool parallelism replaces manual state routing
4. **Prompt caching** — direct cost reduction not available with OpenAI
5. **Reduced boilerplate** — ~50% less orchestration code (graph wiring, state TypedDicts, node edges)

Preserve PostgreSQL for message history and the existing `semantic_cache.py` — these are implementation details, not framework dependencies.

---

*Document prepared for engineering review. Feedback and amendments welcome before Phase 1 kickoff.*
