from typing import TypedDict, Annotated, Sequence, Optional
import operator
import os
from langchain_core.messages import BaseMessage, HumanMessage
from langchain_openai import ChatOpenAI
from langchain_community.tools import DuckDuckGoSearchRun
from langchain_core.utils.function_calling import convert_to_openai_function
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolExecutor, ToolInvocation
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from dotenv import load_dotenv
import json
import logging

# Configure logging for production visibility
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

# ============================================================
# 🎯 ARCHITECT'S NOTE: State Persistence Layer
# ============================================================
# This is what separates a demo from production.
# - Conversations survive container restarts
# - Can "rewind" to any previous state (time travel debugging)
# - Enables human-in-the-loop workflows
# - Supports multi-tenant isolation via thread_id
# ============================================================

# 1. Define the "State"
# This is the "Memory" passed between nodes. It's just a list of messages.
class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], operator.add]

# 2. Setup Tools & Model
search = DuckDuckGoSearchRun()
tools = [search]
tool_executor = ToolExecutor(tools)

model = ChatOpenAI(model="gpt-4o-mini", temperature=0)
# We bind tools to the model so it knows they exist
model = model.bind_functions(tools)

# 3. Define Nodes (The Workers)

def call_model(state):
    """The Brain: Decides what to do next."""
    messages = state['messages']
    response = model.invoke(messages)
    return {"messages": [response]}

def call_tool(state):
    """The Hands: Executes the tool if the Brain asked for it."""
    messages = state['messages']
    last_message = messages[-1]
    
    # Parse the tool call
    function_call = last_message.additional_kwargs["function_call"]
    action = ToolInvocation(
        tool=function_call["name"],
        tool_input=json.loads(function_call["arguments"]),
    )
    
    # Execute
    logger.info(f"⚙️ Executing Tool: {action.tool} with input: {action.tool_input}")
    response = tool_executor.invoke(action)
    
    # Create a message to send back to the Brain
    from langchain_core.messages import FunctionMessage
    function_message = FunctionMessage(content=str(response), name=action.tool)
    
    return {"messages": [function_message]}

# 4. Define Logic (The Router)
def should_continue(state):
    last_message = state['messages'][-1]
    # If the LLM returned a function call, go to "tools"
    if "function_call" in last_message.additional_kwargs:
        return "continue"
    # Otherwise, stop
    return "end"

# 5. Build the Graph (The Architecture)
workflow = StateGraph(AgentState)

workflow.add_node("agent", call_model)
workflow.add_node("action", call_tool)

workflow.set_entry_point("agent") # Start here

# Conditional Edge: agent -> action OR agent -> end
workflow.add_conditional_edges(
    "agent",
    should_continue,
    {
        "continue": "action",
        "end": END
    }
)

# Normal Edge: action -> agent (Loop back to Brain to interpret results)
workflow.add_edge("action", "agent")

# ============================================================
# 🚀 PRODUCTION UPGRADE: PostgreSQL Checkpointer
# ============================================================
# Global connection pool and checkpointer instance
# Initialized lazily on first use to avoid blocking at import time
_checkpointer: Optional[AsyncPostgresSaver] = None

async def get_checkpointer() -> AsyncPostgresSaver:
    """
    Factory function for the checkpointer with connection pooling.
    This creates a singleton instance that's reused across requests.
    """
    global _checkpointer
    
    if _checkpointer is None:
        db_url = os.getenv(
            "DATABASE_URL",
            "postgresql://postgres:password@postgres:5432/compliance_db"
        )
        
        logger.info(f"🔄 Initializing PostgreSQL Checkpointer: {db_url.split('@')[1]}")
        
        # AsyncPostgresSaver handles connection pooling internally
        _checkpointer = AsyncPostgresSaver.from_conn_string(db_url)
        
        # Setup tables if they don't exist
        await _checkpointer.setup()
        logger.info("✅ Checkpointer initialized and tables verified")
    
    return _checkpointer

# Compile graph WITHOUT checkpointer initially (will be added at runtime)
app_graph_stateless = workflow.compile()

# 6. Enhanced Helper Functions with State Persistence

async def run_graph_agent(
    query: str, 
    thread_id: str = "default",
    checkpoint_id: Optional[str] = None
):
    """
    Execute the agent with persistent state.
    
    Args:
        query: The user's question
        thread_id: Unique conversation identifier (maps to user session)
        checkpoint_id: Optional - resume from a specific checkpoint (time travel)
    
    Returns:
        The agent's final response
    """
    checkpointer = await get_checkpointer()
    
    # Compile graph WITH checkpointer for this execution
    app_graph = workflow.compile(checkpointer=checkpointer)
    
    # Configuration for this execution thread
    config = {
        "configurable": {
            "thread_id": thread_id,
        }
    }
    
    # If checkpoint_id provided, add it for time-travel
    if checkpoint_id:
        config["configurable"]["checkpoint_id"] = checkpoint_id
        logger.info(f"🕰️ Time travel: resuming from checkpoint {checkpoint_id}")
    
    inputs = {"messages": [HumanMessage(content=query)]}
    
    logger.info(f"🧠 Agent processing query for thread: {thread_id}")
    result = await app_graph.ainvoke(inputs, config=config)
    
    return result['messages'][-1].content

async def get_conversation_history(thread_id: str, limit: int = 10):
    """
    Retrieve the conversation history for a thread.
    This enables "context-aware" follow-up questions.
    
    Args:
        thread_id: The conversation thread
        limit: Maximum number of checkpoints to retrieve
    
    Returns:
        List of states with metadata
    """
    checkpointer = await get_checkpointer()
    app_graph = workflow.compile(checkpointer=checkpointer)
    
    config = {"configurable": {"thread_id": thread_id}}
    
    history = []
    state_iterator = app_graph.aget_state_history(config)
    
    count = 0
    async for state in state_iterator:
        if count >= limit:
            break
        
        history.append({
            "checkpoint_id": state.config["configurable"].get("checkpoint_id"),
            "messages": [
                {"type": msg.type, "content": msg.content}
                for msg in state.values.get("messages", [])
            ],
            "metadata": state.metadata,
            "parent_config": state.parent_config
        })
        count += 1
    
    return history

async def rewind_conversation(thread_id: str, steps_back: int = 1):
    """
    Time-travel debugging: Rewind the conversation N steps back.
    Useful for correcting errors or exploring alternate paths.
    
    Args:
        thread_id: The conversation thread
        steps_back: Number of steps to rewind
    
    Returns:
        The checkpoint_id to resume from
    """
    history = await get_conversation_history(thread_id, limit=steps_back + 1)
    
    if len(history) <= steps_back:
        raise ValueError(f"Cannot rewind {steps_back} steps - only {len(history)} checkpoints available")
    
    target_checkpoint = history[steps_back]
    logger.info(f"⏪ Rewound {steps_back} steps to checkpoint: {target_checkpoint['checkpoint_id']}")
    
    return target_checkpoint['checkpoint_id']

# ============================================================
# 🎓 ARCHITECT'S INTERVIEW TALKING POINTS:
# ============================================================
# 1. "I implemented PostgreSQL-backed state persistence using LangGraph's
#    AsyncPostgresSaver, which serializes the entire graph state after
#    each node execution."
#
# 2. "This enables production features like conversation resumption after
#    container restarts, time-travel debugging by rewinding to any
#    checkpoint, and human-in-the-loop workflows where agents pause
#    for approval."
#
# 3. "The architecture uses thread_id for multi-tenant isolation - each
#    user's conversation is stored independently."
#
# 4. "Connection pooling is handled at the checkpointer level using
#    asyncpg for non-blocking I/O under load."
# ============================================================
