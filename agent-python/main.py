import os
import json
import asyncio
import time
import logging
from typing import Optional, List, Dict, Any
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from dotenv import load_dotenv
from openai import AsyncOpenAI
from agent import run_agent
from semantic_cache import (
    SemanticCache,
    CacheResult,
    CacheStatus,
    initialize_semantic_cache,
    get_semantic_cache
)
from graph_agent import (
    run_graph_agent, 
    get_conversation_history, 
    rewind_conversation,
    check_pending_approval,
    approve_and_continue
)
from multi_agent_supervisor import run_multi_agent
from generative_ui import (
    fetch_stock_with_chart,
    fetch_comparison_data,
    generate_ui_artifacts,
    build_stock_card,
    build_stock_chart,
    build_comparison_chart,
    build_comparison_table,
    TextArtifact,
    UIArtifact
)

# 1. Load Environment Variables
load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")

if not api_key:
    raise ValueError("❌ No API Key found! Did you create the .env file?")

# 2. Initialize the Async Client
client = AsyncOpenAI(api_key=api_key)

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Database URL for semantic cache (same as graph agent)
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:postgres@localhost:5432/compliance_rag"
)

# Semantic Cache configuration from environment
CACHE_ENABLED = os.getenv("SEMANTIC_CACHE_ENABLED", "true").lower() == "true"
CACHE_TTL = int(os.getenv("SEMANTIC_CACHE_TTL", "300"))  # 5 minutes default
CACHE_SIMILARITY_THRESHOLD = float(os.getenv("SEMANTIC_CACHE_THRESHOLD", "0.92"))


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize services on startup, cleanup on shutdown."""
    # Startup
    logger.info("🚀 Starting AI Service...")
    
    # Initialize semantic cache
    if CACHE_ENABLED:
        try:
            await initialize_semantic_cache(
                database_url=DATABASE_URL,
                similarity_threshold=CACHE_SIMILARITY_THRESHOLD,
                ttl_seconds=CACHE_TTL,
                enabled=True
            )
            logger.info(f"✅ Semantic cache initialized (TTL={CACHE_TTL}s, threshold={CACHE_SIMILARITY_THRESHOLD})")
        except Exception as e:
            logger.error(f"⚠️ Failed to initialize semantic cache: {e}")
            logger.info("Continuing without semantic caching...")
    else:
        logger.info("⏸️ Semantic cache disabled")
    
    yield
    
    # Shutdown
    logger.info("👋 Shutting down AI Service...")


app = FastAPI(
    title="Agentic AI Service", 
    version="6.0.0",
    description="Production-grade AI agent with state persistence, time-travel debugging, Human-in-the-Loop, Multi-Agent Supervisor, Generative UI, and Semantic Caching",
    lifespan=lifespan
)

# ============================================================
# 3. Enhanced DTOs with Session Management + HITL
# ============================================================

class ChatRequest(BaseModel):
    query: str
    thread_id: Optional[str] = None
    enable_hitl: Optional[bool] = False  # Enable Human-in-the-Loop
    
class ChatResponse(BaseModel):
    answer: str
    thread_id: Optional[str] = None
    pending_approval: Optional[bool] = False
    
class HistoryRequest(BaseModel):
    thread_id: str
    limit: Optional[int] = 10

class RewindRequest(BaseModel):
    thread_id: str
    steps_back: int = 1

class ApprovalRequest(BaseModel):
    thread_id: str
    approved: bool

@app.get("/")
async def root():
    cache = get_semantic_cache()
    cache_status = "enabled" if cache and cache.enabled else "disabled"
    
    return {
        "message": "AI Service v6.0 is Online 🤖",
        "features": [
            "State Persistence (survives restarts)",
            "Conversation History",
            "Time Travel Debugging",
            "Human-in-the-Loop (HITL) Approval Flows",
            "Multi-Agent Supervisor Pattern",
            "Generative UI (Streaming Components)",
            f"Semantic Caching ({cache_status}) - NEW!"
        ]
    }

@app.get("/health")
async def health_check():
    cache = get_semantic_cache()
    return {
        "status": "healthy", 
        "version": "6.0.0",
        "cache_enabled": cache.enabled if cache else False
    }

@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    try:
        completion = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a helpful AI assistant."},
                {"role": "user", "content": request.query}
            ]
        )
        
        ai_content = completion.choices[0].message.content
        return ChatResponse(answer=ai_content)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@app.post("/api/agent", response_model=ChatResponse)
async def run_agent_endpoint(request: ChatRequest):
    try:
        response_text = run_agent(request.query)
        return ChatResponse(answer=response_text)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ============================================================
# 🎯 MULTI-AGENT SUPERVISOR PATTERN
# ============================================================

class MultiAgentRequest(BaseModel):
    query: str
    
class MultiAgentResponse(BaseModel):
    answer: str
    agents_used: list[str]
    research_results: Optional[str] = None
    quantitative_results: Optional[str] = None
    success: bool
    cache_hit: Optional[bool] = None
    cache_similarity: Optional[float] = None
    latency_ms: Optional[float] = None


class CacheConfigRequest(BaseModel):
    enabled: Optional[bool] = None
    ttl_seconds: Optional[int] = None
    similarity_threshold: Optional[float] = None


@app.post("/api/multi-agent", response_model=MultiAgentResponse)
async def run_multi_agent_endpoint(request: MultiAgentRequest):
    """
    Execute a query using the Multi-Agent Supervisor Pattern with Semantic Caching.
    
    **Semantic Caching Flow:**
    1. Query embedding is generated
    2. Check cache for semantically similar queries (cosine similarity > threshold)
    3. **Cache Hit**: Return cached response (0ms LLM latency, $0 cost)
    4. **Cache Miss**: Execute agents → Store response in cache
    
    This endpoint routes requests through a hierarchical agent system:
    
    - **Supervisor**: Routes tasks to specialized workers (never calls tools)
    - **Research Agent**: Web search, fact-finding (Tavily)
    - **Quantitative Agent**: Stock analysis, calculations (yfinance, pandas)
    - **Writer Agent**: Formats final response (no tools, pure LLM)
    
    **Example queries:**
    - "What is the stock price of Apple?" → Quant Agent
    - "What are the latest AI news?" → Research Agent
    - "Analyze Tesla stock and market sentiment" → Research + Quant + Writer
    
    **Cache Benefits:**
    - 50 users asking similar questions = 1 LLM call
    - ~0ms cache hit latency vs ~2000ms LLM latency
    - Estimated $0.03 saved per cache hit
    """
    start_time = time.time()
    cache = get_semantic_cache()
    cache_hit = False
    cache_similarity = None
    
    try:
        # Check semantic cache first
        if cache and cache.enabled:
            cache_result = await cache.get(request.query)
            
            if cache_result.status == CacheStatus.HIT:
                # Cache hit! Return cached response
                latency_ms = (time.time() - start_time) * 1000
                logger.info(f"✅ Cache HIT (similarity={cache_result.similarity:.3f}): {request.query[:50]}...")
                
                return MultiAgentResponse(
                    answer=cache_result.response,
                    agents_used=["cache"],
                    research_results=None,
                    quantitative_results=None,
                    success=True,
                    cache_hit=True,
                    cache_similarity=cache_result.similarity,
                    latency_ms=latency_ms
                )
            else:
                logger.info(f"❌ Cache MISS: {request.query[:50]}...")
        
        # Cache miss - execute multi-agent
        result = await run_multi_agent(request.query)
        answer = result.get("answer", "")
        
        # Store in cache for future requests
        if cache and cache.enabled and answer:
            await cache.set(
                query=request.query,
                response=answer,
                metadata={
                    "agents_used": result.get("agent_trace", {}).get("agents_used", []),
                    "source": "multi-agent"
                }
            )
            logger.info(f"💾 Cached response for: {request.query[:50]}...")
        
        latency_ms = (time.time() - start_time) * 1000
        
        return MultiAgentResponse(
            answer=answer,
            agents_used=result.get("agent_trace", {}).get("agents_used", []),
            research_results=result.get("agent_trace", {}).get("research_results"),
            quantitative_results=result.get("agent_trace", {}).get("quantitative_results"),
            success=result.get("success", False),
            cache_hit=False,
            cache_similarity=None,
            latency_ms=latency_ms
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# 🎨 GENERATIVE UI - Streaming Components
# ============================================================

class GenerativeUIRequest(BaseModel):
    query: str
    stream: Optional[bool] = True  # Enable streaming by default


def parse_stock_symbols(query: str) -> List[str]:
    """Extract stock symbols from a query."""
    import re
    # Common stock symbols in parentheses or mentioned directly
    symbols = []
    
    # Match explicit symbols like (AAPL), (GOOGL), etc.
    explicit = re.findall(r'\(([A-Z]{1,5})\)', query.upper())
    symbols.extend(explicit)
    
    # Match company names to symbols
    company_map = {
        'apple': 'AAPL',
        'google': 'GOOGL',
        'alphabet': 'GOOGL',
        'microsoft': 'MSFT',
        'amazon': 'AMZN',
        'tesla': 'TSLA',
        'meta': 'META',
        'facebook': 'META',
        'nvidia': 'NVDA',
        'netflix': 'NFLX',
        'amd': 'AMD',
        'intel': 'INTC',
        'ibm': 'IBM',
        'salesforce': 'CRM',
        'adobe': 'ADBE',
        'oracle': 'ORCL',
        'cisco': 'CSCO',
        'paypal': 'PYPL',
        'uber': 'UBER',
        'lyft': 'LYFT',
        'spotify': 'SPOT',
        'zoom': 'ZM',
        'slack': 'WORK',
        'twitter': 'X',
        'snap': 'SNAP',
        'pinterest': 'PINS'
    }
    
    query_lower = query.lower()
    for company, symbol in company_map.items():
        if company in query_lower and symbol not in symbols:
            symbols.append(symbol)
    
    return symbols[:4]  # Limit to 4 for comparison


async def generate_stream_events(query: str):
    """
    Generator that yields Server-Sent Events with UI artifacts.
    
    Flow:
    1. Yield "thinking" event
    2. Detect visualization type
    3. Fetch data
    4. Yield artifact events (charts, cards, tables)
    5. Yield text summary from multi-agent
    6. Yield "done" event
    """
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        # 1. Signal that we're thinking
        yield f"data: {json.dumps({'type': 'status', 'message': 'Analyzing your request...'})}\n\n"
        await asyncio.sleep(0.1)  # Small delay for UX
        
        # 2. Parse symbols from query
        symbols = parse_stock_symbols(query)
        logger.info(f"🎨 Generative UI: Detected symbols: {symbols}")
        
        if not symbols:
            # No stock symbols detected - use regular multi-agent
            yield f"data: {json.dumps({'type': 'status', 'message': 'Processing with AI agents...'})}\n\n"
            
            result = await run_multi_agent(query)
            
            # Yield text response
            text_artifact = TextArtifact(content=result.get("answer", ""))
            yield f"data: {json.dumps({'type': 'artifact', 'artifact': text_artifact.model_dump()})}\n\n"
            
            yield f"data: {json.dumps({'type': 'done', 'agents_used': result.get('agent_trace', {}).get('agents_used', [])})}\n\n"
            return
        
        # 3. Stock query detected - fetch data and generate artifacts
        is_comparison = len(symbols) > 1 or any(word in query.lower() for word in ["compare", "vs", "versus"])
        
        if is_comparison and len(symbols) >= 2:
            # Multi-stock comparison
            status_msg = f"Fetching data for {', '.join(symbols)}..."
            yield f"data: {json.dumps({'type': 'status', 'message': status_msg})}\n\n"
            
            data = fetch_comparison_data(symbols, period="1mo")
            
            if data.get("stocks"):
                # Yield comparison chart
                yield f"data: {json.dumps({'type': 'status', 'message': 'Generating comparison chart...'})}\n\n"
                await asyncio.sleep(0.1)
                
                chart = build_comparison_chart(symbols, data.get("history", {}))
                yield f"data: {json.dumps({'type': 'artifact', 'artifact': chart.model_dump()})}\n\n"
                await asyncio.sleep(0.2)
                
                # Yield comparison table
                yield f"data: {json.dumps({'type': 'status', 'message': 'Building comparison table...'})}\n\n"
                table = build_comparison_table(data["stocks"])
                yield f"data: {json.dumps({'type': 'artifact', 'artifact': table.model_dump()})}\n\n"
                await asyncio.sleep(0.2)
                
                # Yield individual stock cards
                for symbol, info in data["stocks"].items():
                    card = build_stock_card(symbol, info)
                    yield f"data: {json.dumps({'type': 'artifact', 'artifact': card.model_dump()})}\n\n"
                    await asyncio.sleep(0.1)
        else:
            # Single stock
            symbol = symbols[0]
            status_msg = f"Fetching {symbol} stock data..."
            yield f"data: {json.dumps({'type': 'status', 'message': status_msg})}\n\n"
            
            data = fetch_stock_with_chart(symbol, period="1mo")
            
            if "info" in data:
                # Yield stock card
                yield f"data: {json.dumps({'type': 'status', 'message': 'Building stock card...'})}\n\n"
                card = build_stock_card(symbol, data["info"])
                yield f"data: {json.dumps({'type': 'artifact', 'artifact': card.model_dump()})}\n\n"
                await asyncio.sleep(0.2)
                
                # Yield price chart
                if data.get("history"):
                    yield f"data: {json.dumps({'type': 'status', 'message': 'Generating price chart...'})}\n\n"
                    chart = build_stock_chart(symbol, data["history"])
                    yield f"data: {json.dumps({'type': 'artifact', 'artifact': chart.model_dump()})}\n\n"
        
        # 4. Get text analysis from multi-agent
        yield f"data: {json.dumps({'type': 'status', 'message': 'Generating analysis...'})}\n\n"
        result = await run_multi_agent(query)
        
        # Yield text summary
        text_artifact = TextArtifact(content=result.get("answer", ""))
        yield f"data: {json.dumps({'type': 'artifact', 'artifact': text_artifact.model_dump()})}\n\n"
        
        # 5. Done
        yield f"data: {json.dumps({'type': 'done', 'agents_used': result.get('agent_trace', {}).get('agents_used', [])})}\n\n"
        
    except Exception as e:
        logger.error(f"❌ Generative UI error: {str(e)}")
        yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"


@app.post("/api/generative-ui")
async def generative_ui_endpoint(request: GenerativeUIRequest):
    """
    🎨 Generative UI - Stream rich UI components to the frontend.
    
    Instead of plain text, this endpoint streams structured JSON artifacts
    that the frontend renders as interactive charts, tables, and cards.
    
    **Supported Artifact Types:**
    - `line_chart`: Time series data (stock prices, trends)
    - `bar_chart`: Category comparisons
    - `data_table`: Structured data tables
    - `stock_card`: Rich stock information cards
    - `comparison_card`: Side-by-side comparisons
    - `text`: Plain text (fallback)
    
    **Example Queries:**
    - "What is Apple's stock price?" → StockCard + LineChart
    - "Compare Google and Microsoft stock" → ComparisonChart + Table + Cards
    
    **Response Format (Server-Sent Events):**
    ```
    data: {"type": "status", "message": "Analyzing..."}
    data: {"type": "artifact", "artifact": {"type": "stock_card", ...}}
    data: {"type": "artifact", "artifact": {"type": "line_chart", ...}}
    data: {"type": "done", "agents_used": ["Quantitative Agent"]}
    ```
    
    **Why This Pattern:**
    - Real-time streaming creates engaging UX
    - Frontend renders rich visualizations, not plain text
    - Demonstrates "Full Stack AI" capability
    """
    if request.stream:
        return StreamingResponse(
            generate_stream_events(request.query),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no"  # Disable nginx buffering
            }
        )
    else:
        # Non-streaming fallback
        symbols = parse_stock_symbols(request.query)
        artifacts = []
        
        if symbols:
            if len(symbols) >= 2:
                data = fetch_comparison_data(symbols)
                artifacts = await generate_ui_artifacts(request.query, data)
            else:
                data = fetch_stock_with_chart(symbols[0])
                artifacts = await generate_ui_artifacts(request.query, data)
        
        result = await run_multi_agent(request.query)
        
        return {
            "artifacts": [a.model_dump() for a in artifacts],
            "text": result.get("answer", ""),
            "agents_used": result.get("agent_trace", {}).get("agents_used", []),
            "success": True
        }

# ============================================================
# 🚀 PRODUCTION ENDPOINTS: Stateful Conversations
# ============================================================

@app.post("/api/graph", response_model=ChatResponse)
async def run_graph_endpoint(request: ChatRequest):
    """
    Execute the agent with PostgreSQL-backed state persistence.
    
    - If thread_id is provided, conversation continues from previous state
    - If thread_id is None, a new conversation is started
    - enable_hitl: Enable Human-in-the-Loop for high-risk operations
    - State survives container restarts
    """
    try:
        thread_id = request.thread_id or "default"
        
        result = await run_graph_agent(
            query=request.query,
            thread_id=thread_id,
            enable_hitl=request.enable_hitl or False
        )
        
        # If result is a dict (HITL pause), extract fields
        if isinstance(result, dict):
            return ChatResponse(
                answer=result.get("answer", ""),
                thread_id=thread_id,
                pending_approval=result.get("pending_approval", False)
            )
        
        # If result is a string (normal flow)
        return ChatResponse(
            answer=result,
            thread_id=thread_id,
            pending_approval=False
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/graph/history")
async def get_history_endpoint(request: HistoryRequest):
    """
    Retrieve the conversation history for a thread.
    
    Returns all checkpoints (state snapshots) for time-travel debugging.
    """
    try:
        history = await get_conversation_history(
            thread_id=request.thread_id,
            limit=request.limit or 10
        )
        
        return {
            "thread_id": request.thread_id,
            "checkpoint_count": len(history),
            "history": history
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/graph/rewind")
async def rewind_endpoint(request: RewindRequest):
    """
    Time-travel debugging: Rewind a conversation N steps back.
    
    Useful for correcting agent mistakes and exploring alternate paths.
    """
    try:
        checkpoint_id = await rewind_conversation(
            thread_id=request.thread_id,
            steps_back=request.steps_back
        )
        
        return {
            "thread_id": request.thread_id,
            "checkpoint_id": checkpoint_id,
            "message": f"Rewound {request.steps_back} steps"
        }
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ============================================================
# 🔐 HITL (Human-in-the-Loop) ENDPOINTS
# ============================================================

@app.post("/api/graph/pending")
async def check_pending_endpoint(request: HistoryRequest):
    """
    Check if a conversation is waiting for human approval.
    
    Returns pending tool call details if the graph is paused at an interrupt.
    Use this before showing Approve/Reject UI to the user.
    """
    try:
        result = await check_pending_approval(request.thread_id)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/graph/approve")
async def approve_endpoint(request: ApprovalRequest):
    """
    Approve or reject a pending high-risk action.
    
    - approved=True: Execute the pending tool and continue graph execution
    - approved=False: Cancel the action and respond with rejection message
    
    This resumes the graph from the interrupt point.
    """
    try:
        action = "approved" if request.approved else "rejected"
        result = await approve_and_continue(
            thread_id=request.thread_id,
            approved=request.approved
        )
        
        return {
            "thread_id": request.thread_id,
            "action": action,
            "result": result
        }
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# 💾 SEMANTIC CACHE MANAGEMENT ENDPOINTS
# ============================================================

@app.get("/api/cache/stats")
async def get_cache_stats():
    """
    Get semantic cache statistics.
    
    Returns:
    - Total queries processed
    - Cache hits/misses
    - Hit rate percentage
    - Estimated cost savings
    - Average latency for hits vs misses
    
    **Use Case**: Monitor cache efficiency in production.
    """
    cache = get_semantic_cache()
    if not cache:
        return {"enabled": False, "message": "Semantic cache not initialized"}
    
    stats = await cache.get_stats()
    
    return {
        "enabled": cache.enabled,
        "config": {
            "ttl_seconds": cache.ttl_seconds,
            "similarity_threshold": cache.similarity_threshold,
            "max_cache_size": cache.max_cache_size
        },
        "stats": {
            "total_queries": stats.total_queries,
            "cache_hits": stats.cache_hits,
            "cache_misses": stats.cache_misses,
            "hit_rate_percent": round(stats.hit_rate, 2),
            "estimated_cost_saved_usd": round(stats.estimated_cost_saved, 2),
            "avg_hit_latency_ms": round(stats.avg_hit_latency_ms, 2),
            "avg_miss_latency_ms": round(stats.avg_miss_latency_ms, 2)
        }
    }


@app.get("/api/cache/entries")
async def get_cache_entries(limit: int = 50):
    """
    List recent cache entries for monitoring.
    
    Shows query text, response preview, hit count, and expiration.
    Useful for debugging and understanding cache behavior.
    """
    cache = get_semantic_cache()
    if not cache:
        return {"enabled": False, "entries": []}
    
    entries = await cache.get_cache_entries(limit=limit)
    
    # Convert datetime objects to strings for JSON serialization
    for entry in entries:
        for key in ["created_at", "expires_at", "last_hit_at"]:
            if entry.get(key):
                entry[key] = entry[key].isoformat()
    
    return {"enabled": cache.enabled, "count": len(entries), "entries": entries}


@app.post("/api/cache/config")
async def update_cache_config(config: CacheConfigRequest):
    """
    Update cache configuration at runtime.
    
    **Parameters:**
    - `enabled`: Enable/disable caching
    - `ttl_seconds`: Time-to-live for cache entries
    - `similarity_threshold`: Minimum similarity for cache hit (0-1)
    
    **Example:**
    ```json
    {"enabled": true, "ttl_seconds": 600, "similarity_threshold": 0.90}
    ```
    """
    cache = get_semantic_cache()
    if not cache:
        raise HTTPException(status_code=503, detail="Semantic cache not initialized")
    
    if config.enabled is not None:
        if config.enabled:
            cache.enable()
        else:
            cache.disable()
    
    if config.ttl_seconds is not None:
        cache.set_ttl(config.ttl_seconds)
    
    if config.similarity_threshold is not None:
        cache.set_threshold(config.similarity_threshold)
    
    return {
        "message": "Cache configuration updated",
        "config": {
            "enabled": cache.enabled,
            "ttl_seconds": cache.ttl_seconds,
            "similarity_threshold": cache.similarity_threshold
        }
    }


@app.delete("/api/cache")
async def invalidate_cache(query: Optional[str] = None):
    """
    Invalidate cache entries.
    
    - No query parameter: Invalidate ALL cache entries
    - With query parameter: Invalidate specific query only
    
    **Use Case**: Clear stale data or reset for testing.
    """
    cache = get_semantic_cache()
    if not cache:
        raise HTTPException(status_code=503, detail="Semantic cache not initialized")
    
    count = await cache.invalidate(query=query)
    
    return {
        "message": f"Invalidated {count} cache entries",
        "query": query,
        "count": count
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)

