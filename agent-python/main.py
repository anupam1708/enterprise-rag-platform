import os
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from dotenv import load_dotenv
from openai import AsyncOpenAI
from agent import run_agent  # <--- Import your new function
from graph_agent import run_graph_agent # <--- New Import

# 1. Load Environment Variables (Like Spring @Value)
load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")

if not api_key:
    raise ValueError("❌ No API Key found! Did you create the .env file?")

# 2. Initialize the Async Client (Non-blocking I/O)
client = AsyncOpenAI(api_key=api_key)

app = FastAPI(title="Agentic AI Service", version="1.0.0")

# 3. Define DTOs using Pydantic (Like Java Records/POJOs)
# This enforces that the user MUST send a JSON with a "query" field.
class ChatRequest(BaseModel):
    query: str

class ChatResponse(BaseModel):
    answer: str

@app.get("/")
async def root():
    return {"message": "AI Service is Online 🤖"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

# 4. The AI Endpoint
@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    try:
        # Call OpenAI (Notice the 'await' keyword - this frees up the thread)
        completion = await client.chat.completions.create(
            model="gpt-4o-mini",  # Using the faster/cheaper model for dev
            messages=[
                {"role": "system", "content": "You are a helpful AI assistant."},
                {"role": "user", "content": request.query}
            ]
        )
        
        # Extract the text
        ai_content = completion.choices[0].message.content
        
        return ChatResponse(answer=ai_content)

    except Exception as e:
        # Return a clean 500 error if OpenAI fails
        raise HTTPException(status_code=500, detail=str(e))
    
@app.post("/api/agent", response_model=ChatResponse)
async def run_agent_endpoint(request: ChatRequest):
    try:
        # Calls the LangChain Agent
        response_text = run_agent(request.query)
        return ChatResponse(answer=response_text)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/graph", response_model=ChatResponse)
async def run_graph_endpoint(request: ChatRequest):
    try:
        response_text = run_graph_agent(request.query)
        return ChatResponse(answer=response_text)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# 5. Run the app with: uvicorn main:app --reload  

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)