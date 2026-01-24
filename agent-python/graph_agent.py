from typing import TypedDict, Annotated, Sequence
import operator
from langchain_core.messages import BaseMessage, HumanMessage
from langchain_openai import ChatOpenAI
from langchain_community.tools import DuckDuckGoSearchRun
from langchain_core.utils.function_calling import convert_to_openai_function
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolExecutor, ToolInvocation
from dotenv import load_dotenv
import json

load_dotenv()

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
    print(f"⚙️ Executing Tool: {action.tool} with input: {action.tool_input}")
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

app_graph = workflow.compile()

# 6. Helper to run it
def run_graph_agent(query: str):
    inputs = {"messages": [HumanMessage(content=query)]}
    result = app_graph.invoke(inputs)
    return result['messages'][-1].content