# Multi-Agent Supervisor Pattern Explained

## The Problem It Solves

A single agent with 20+ tools becomes unreliable - it struggles to pick the right tool, hallucinates tool usage, and makes poor decisions. This is the "Jack of All Trades" anti-pattern.

## The Solution: Hierarchical Multi-Agent System

```
┌─────────────────────────────────────────────────────────────────┐
│                        SUPERVISOR                                │
│         (Routes requests, NEVER calls tools directly)            │
│                              │                                   │
│     ┌────────────────────────┼────────────────────────┐         │
│     ▼                        ▼                        ▼         │
│ ┌─────────┐          ┌─────────────┐          ┌─────────────┐   │
│ │RESEARCH │          │QUANTITATIVE │          │   WRITER    │   │
│ │  AGENT  │          │    AGENT    │          │   AGENT     │   │
│ ├─────────┤          ├─────────────┤          ├─────────────┤   │
│ │DuckDuck │          │  yfinance   │          │  No tools   │   │
│ │   Go    │          │   Pandas    │          │  Pure LLM   │   │
│ └─────────┘          └─────────────┘          └─────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

---

## Code Breakdown

### 1. Shared State Definition

```python
class MultiAgentState(TypedDict):
    """State shared across all agents in the supervisor pattern."""
    messages: Annotated[Sequence[BaseMessage], operator.add]
    next_agent: str              # Which agent should run next
    research_results: str        # Accumulated research findings
    quantitative_results: str    # Stock/financial analysis results
    final_report: str            # Formatted output from writer
    task_complete: bool          # Flag to indicate completion
```

**Key Insight:** All agents share this state. The supervisor reads it to decide routing, workers write their results to it.

---

### 2. Specialized Tools Per Agent

**Research Agent Tools:**
```python
@tool
def web_search(query: str) -> str:
    """Search the web for current information."""
    results = search_tool.run(query)
    return f"Search Results:\n{results}"
```

**Quantitative Agent Tools:**
```python
@tool
def get_stock_price(symbol: str) -> str:
    """Get current stock price using yfinance."""
    import yfinance as yf
    ticker = yf.Ticker(symbol)
    info = ticker.info
    return f"Stock: {symbol}, Price: ${info.get('currentPrice')}"
```

**Writer Agent:** No tools! Pure LLM for formatting.

---

### 3. The Supervisor Node

```python
SUPERVISOR_SYSTEM_PROMPT = """You are a Supervisor Agent that routes tasks.
You NEVER call tools yourself. You only decide which worker should handle the task.

Your workers:
1. RESEARCH_AGENT: Web searches, facts, news
2. QUANT_AGENT: Stock prices, financial analysis, calculations
3. WRITER_AGENT: Formatting reports, final responses

Respond with ONLY one of: RESEARCH_AGENT, QUANT_AGENT, WRITER_AGENT, or FINISH
"""

def supervisor_node(state: MultiAgentState) -> Dict[str, Any]:
    """Supervisor decides which agent should work next."""
    messages = state["messages"]
    research_results = state.get("research_results", "")
    quant_results = state.get("quantitative_results", "")
    
    # Build context showing what's been done
    context = f"""
    User Request: {messages[-1].content}
    Research Results: {research_results or 'None yet'}
    Quantitative Results: {quant_results or 'None yet'}
    
    Decide which agent should work next.
    """
    
    response = supervisor_model.invoke([
        SystemMessage(content=SUPERVISOR_SYSTEM_PROMPT),
        HumanMessage(content=context)
    ])
    
    # Parse decision
    decision = response.content.strip().upper()
    if "RESEARCH" in decision:
        return {"next_agent": "research_agent"}
    elif "QUANT" in decision:
        return {"next_agent": "quant_agent"}
    elif "WRITER" in decision:
        return {"next_agent": "writer_agent"}
    else:
        return {"next_agent": "finish"}
```

**Key Insight:** The supervisor has NO tools bound. It only reads state and makes routing decisions.

---

### 4. Worker Agent Nodes

Each worker follows the same pattern:

```python
def quant_agent_node(state: MultiAgentState) -> Dict[str, Any]:
    """Quantitative agent analyzes financial data."""
    user_query = state["messages"][-1].content
    
    # Agent has tools bound
    response = quant_model_with_tools.invoke([
        SystemMessage(content=QUANT_SYSTEM_PROMPT),
        HumanMessage(content=f"Analyze: {user_query}")
    ])
    
    # Execute any tool calls
    results = []
    if response.tool_calls:
        for tool_call in response.tool_calls:
            result = quant_executor.invoke(ToolInvocation(
                tool=tool_call["name"],
                tool_input=tool_call["args"]
            ))
            results.append(result)
    
    # Write results to shared state
    return {
        "quantitative_results": "\n".join(results),
        "messages": [AIMessage(content=f"[Quant Agent] {results}")]
    }
```

---

### 5. The StateGraph

```python
def create_multi_agent_graph():
    workflow = StateGraph(MultiAgentState)
    
    # Add all nodes
    workflow.add_node("supervisor", supervisor_node)
    workflow.add_node("research_agent", research_agent_node)
    workflow.add_node("quant_agent", quant_agent_node)
    workflow.add_node("writer_agent", writer_agent_node)
    
    # Entry point
    workflow.set_entry_point("supervisor")
    
    # Supervisor routes to workers
    workflow.add_conditional_edges(
        "supervisor",
        route_after_supervisor,
        {
            "research_agent": "research_agent",
            "quant_agent": "quant_agent",
            "writer_agent": "writer_agent",
            "finish": END
        }
    )
    
    # Workers loop back to supervisor
    workflow.add_conditional_edges(
        "research_agent",
        should_continue_after_worker,
        {"supervisor": "supervisor", "finish": END}
    )
    
    # Writer always finishes
    workflow.add_edge("writer_agent", END)
    
    return workflow.compile()
```

---

### 6. Execution Flow Example

**Query:** "What is Apple's stock price and recent performance?"

```
1. SUPERVISOR receives query
   → Analyzes: "stock price" → Routes to QUANT_AGENT

2. QUANT_AGENT runs
   → Calls get_stock_price("AAPL")
   → Calls get_stock_history("AAPL", "1mo")
   → Writes results to state.quantitative_results
   → Returns to SUPERVISOR

3. SUPERVISOR checks state
   → quant_results: ✅ Has data
   → research_results: ❌ Empty
   → Decision: WRITER_AGENT (enough info)

4. WRITER_AGENT formats response
   → Reads quantitative_results from state
   → Creates formatted report
   → Sets task_complete = True
   → END
```

---

## Why This Wins Interviews

| Concept | What It Demonstrates |
|---------|---------------------|
| **Separation of Concerns** | Each agent is a specialist, not a generalist |
| **LangGraph StateGraph** | Modern orchestration, not simple chains |
| **Observability** | `agent_trace` shows exactly which agents ran |
| **Scalability** | Easy to add new specialized agents |
| **Error Isolation** | One agent failing doesn't crash the system |
| **Enterprise Pattern** | How production AI systems are actually built |

---

## API Endpoint

```bash
POST /api/multi-agent
Content-Type: application/json

{
  "query": "What is the stock price of Apple and how has it performed?"
}
```

## API Response

```json
{
  "answer": "## Apple Stock Analysis\n\n**Current Price:** $178.50...",
  "agents_used": ["Quantitative Agent", "Writer Agent"],
  "quantitative_results": "Stock: AAPL\nPrice: $178.50...",
  "success": true
}
```

The `agents_used` field provides **full observability** into which specialists handled the request - perfect for debugging and monitoring in production.

---

## File Structure

```
agent-python/
├── multi_agent_supervisor.py    # Main implementation
├── main.py                      # FastAPI endpoint /api/multi-agent
└── MULTI_AGENT_SUPERVISOR_README.md  # This documentation
```

## Testing

```bash
# Test via curl
curl -X POST "http://localhost:8000/api/multi-agent" \
  -H "Content-Type: application/json" \
  -d '{"query": "Analyze Tesla stock performance"}'

# Production URL
curl -X POST "https://hnsworld.ai/api/multi-agent" \
  -H "Content-Type: application/json" \
  -d '{"query": "What is the current stock price of Apple?"}'
```

## Key Takeaways for Portfolio

1. **Supervisor Pattern** - Shows you understand agent orchestration
2. **Separation of Concerns** - Each agent has a single responsibility
3. **LangGraph StateGraph** - Modern, production-grade framework
4. **Observable** - Full trace of which agents handled the request
5. **Extensible** - Easy to add new specialized agents (e.g., Email Agent, Database Agent)
