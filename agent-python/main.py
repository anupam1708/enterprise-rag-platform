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
    rewind_conversation
)

# 1. Load Environment Variables
load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")

if not api_key:
    raise ValueError("❌ No API Key found! Did you create the .env file?")

# 2. Initialize the Async Client
client = AsyncOpenAI(api_key=api_key)

app = FastAPI(
    title="Agentic AI Service", 
    version="2.0.0",
    description="Production-grade AI agent with state persistence and time-travel debugging"
)

# ============================================================
# 3. Enhanced DTOs with Session Management
# ============================================================

class ChatRequest(BaseModel):
    query: str
    thread_id: Optional[str] = None
    
class ChatResponse(BaseModel):
    answer: str
    thread_id: Optional[str] = None
    
class HistoryRequest(BaseModel):
    thread_id: str
    limit: Optional[int] = 10

class RewindRequest(BaseModel):
    thread_id: str
    steps_back: int = 1

@app.get("/")
async def root():
    return {
        "message": "AI Service v2.0 is Online 🤖",
        "features": [
            "State Persistence (survives restarts)",
            "Conversation History",
            "Time Travel Debugging"
        ]
    }

@app.get("/health")
async def health_check():
    return {"status": "healthy", "version": "2.0.0"}

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
# 🚀 PRODUCTION ENDPOINTS: Stateful Conversations
# ============================================================

@app.post("/api/graph", response_model=ChatResponse)
async def run_graph_endpoint(request: ChatRequest):
    """
    Execute the agent with PostgreSQL-backed state persistence.
    
    - If thread_id is provided, conversation continues from previous state
    - If thread_id is None, a new conversation is started
    - State survives container restarts
    """
    try:
        thread_id = request.thread_id or "default"
        
        response_text = await run_graph_agent(
            query=request.query,
            thread_id=thread_id
        )
        
        return ChatResponse(
            answer=response_text,
            thread_id=thread_id
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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
