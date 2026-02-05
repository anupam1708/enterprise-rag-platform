import os
from typing import Optional
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from dotenv import load_dotenv
from openai import AsyncOpenAI
from agent import run_agent
from graph_agent import (
    run_graph_agent, 
    get_conversation_history, 
    rewind_conversation,
    check_pending_approval,
    approve_and_continue
)
from multi_agent_supervisor import run_multi_agent

# 1. Load Environment Variables
load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")

if not api_key:
    raise ValueError("❌ No API Key found! Did you create the .env file?")

# 2. Initialize the Async Client
client = AsyncOpenAI(api_key=api_key)

app = FastAPI(
    title="Agentic AI Service", 
    version="4.0.0",
    description="Production-grade AI agent with state persistence, time-travel debugging, Human-in-the-Loop, and Multi-Agent Supervisor patterns"
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
    return {
        "message": "AI Service v4.0 is Online 🤖",
        "features": [
            "State Persistence (survives restarts)",
            "Conversation History",
            "Time Travel Debugging",
            "Human-in-the-Loop (HITL) Approval Flows",
            "Multi-Agent Supervisor Pattern (NEW!)"
        ]
    }

@app.get("/health")
async def health_check():
    return {"status": "healthy", "version": "4.0.0"}

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

@app.post("/api/multi-agent", response_model=MultiAgentResponse)
async def run_multi_agent_endpoint(request: MultiAgentRequest):
    """
    Execute a query using the Multi-Agent Supervisor Pattern.
    
    This endpoint routes requests through a hierarchical agent system:
    
    - **Supervisor**: Routes tasks to specialized workers (never calls tools)
    - **Research Agent**: Web search, fact-finding (DuckDuckGo)
    - **Quantitative Agent**: Stock analysis, calculations (yfinance, pandas)
    - **Writer Agent**: Formats final response (no tools, pure LLM)
    
    The supervisor decides which agent(s) should handle the request,
    enabling separation of concerns and more reliable responses.
    
    **Example queries:**
    - "What is the stock price of Apple?" → Quant Agent
    - "What are the latest AI news?" → Research Agent
    - "Analyze Tesla stock and market sentiment" → Research + Quant + Writer
    """
    try:
        result = await run_multi_agent(request.query)
        
        return MultiAgentResponse(
            answer=result.get("answer", ""),
            agents_used=result.get("agent_trace", {}).get("agents_used", []),
            research_results=result.get("agent_trace", {}).get("research_results"),
            quantitative_results=result.get("agent_trace", {}).get("quantitative_results"),
            success=result.get("success", False)
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)

