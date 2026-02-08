"""
============================================================
🎯 MULTI-AGENT SUPERVISOR PATTERN
============================================================
This is the "Enterprise Pattern" for GenAI agents.

THE PROBLEM:
A single agent with 20 tools becomes a "Jack of All Trades, Master of None".
It struggles to pick the right tool, hallucinates tool usage, and is unreliable.

THE SOLUTION:
Implement a Hierarchical Multi-Agent System with Separation of Concerns:

┌─────────────────────────────────────────────────────────────────┐
│                        SUPERVISOR                                │
│         (Routes requests, never calls tools directly)            │
│                              │                                   │
│     ┌────────────────────────┼────────────────────────┐         │
│     ▼                        ▼                        ▼         │
│ ┌─────────┐          ┌─────────────┐          ┌─────────────┐   │
│ │RESEARCH │          │QUANTITATIVE │          │   WRITER    │   │
│ │  AGENT  │          │    AGENT    │          │   AGENT     │   │
│ ├─────────┤          ├─────────────┤          ├─────────────┤   │
│ │DuckDuck │          │  yfinance   │          │  No tools   │   │
│ │   Go    │          │   Pandas    │          │  Pure LLM   │   │
│ │ Scraper │          │   Math      │          │ formatting  │   │
│ └─────────┘          └─────────────┘          └─────────────┘   │
└─────────────────────────────────────────────────────────────────┘

WHY THIS WINS INTERVIEWS:
- Shows understanding of Separation of Concerns in GenAI
- Demonstrates knowledge of LangGraph's StateGraph
- Reflects how enterprises build reliable multi-agent systems
- Enables parallel execution and specialized error handling

Tech Stack: LangGraph StateGraph with supervisor node
============================================================
"""

from typing import TypedDict, Annotated, Sequence, Literal, List, Dict, Any
import operator
import os
import json
import logging
from datetime import datetime

from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langchain_community.tools.tavily_search import TavilySearchResults
from langchain_core.tools import tool
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolExecutor, ToolInvocation
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

# ============================================================
# 🎯 SHARED STATE DEFINITION
# ============================================================

class MultiAgentState(TypedDict):
    """State shared across all agents in the supervisor pattern."""
    messages: Annotated[Sequence[BaseMessage], operator.add]
    next_agent: str  # Which agent should run next
    research_results: str  # Accumulated research findings
    quantitative_results: str  # Stock/financial analysis results
    final_report: str  # Formatted output from writer
    task_complete: bool  # Flag to indicate completion

# ============================================================
# 🔧 SPECIALIZED TOOLS FOR EACH AGENT
# ============================================================

# --- Research Agent Tools ---
search_tool = TavilySearchResults(max_results=5, search_depth="advanced", time_range="month")

@tool
def web_search(query: str) -> str:
    """Search the web for current information on any topic.

    Args:
        query: The search query to find information about
    """
    current_date = datetime.now().strftime("%B %Y")
    dated_query = f"{query} {current_date}"
    logger.info(f"🔍 Research Agent: Searching for '{dated_query}'")
    try:
        results = search_tool.invoke(dated_query)
        if isinstance(results, list):
            formatted = "\n\n".join(
                f"Source: {r.get('url', 'N/A')}\n{r.get('content', '')}"
                for r in results
            )
            return f"Search Results:\n{formatted}"
        return f"Search Results:\n{results}"
    except Exception as e:
        return f"Search failed: {str(e)}"

@tool
def scrape_summary(url: str) -> str:
    """Get a summary of content from a URL (simulated for demo).
    
    Args:
        url: The URL to scrape and summarize
    """
    logger.info(f"🌐 Research Agent: Scraping '{url}'")
    # In production, use BeautifulSoup or similar
    return f"Scraped content from {url}: [Summary of key points would appear here]"

# --- Quantitative Agent Tools ---
@tool
def get_stock_price(symbol: str) -> str:
    """Get current stock price and basic info for a ticker symbol.
    
    Args:
        symbol: Stock ticker symbol (e.g., 'AAPL', 'GOOGL', 'MSFT')
    """
    logger.info(f"📈 Quantitative Agent: Getting stock price for '{symbol}'")
    try:
        import yfinance as yf
        ticker = yf.Ticker(symbol)
        info = ticker.info
        
        current_price = info.get('currentPrice', info.get('regularMarketPrice', 'N/A'))
        prev_close = info.get('previousClose', 'N/A')
        market_cap = info.get('marketCap', 'N/A')
        pe_ratio = info.get('trailingPE', 'N/A')
        
        # Format market cap
        if isinstance(market_cap, (int, float)):
            if market_cap >= 1e12:
                market_cap_str = f"${market_cap/1e12:.2f}T"
            elif market_cap >= 1e9:
                market_cap_str = f"${market_cap/1e9:.2f}B"
            else:
                market_cap_str = f"${market_cap/1e6:.2f}M"
        else:
            market_cap_str = str(market_cap)
        
        return f"""
Stock: {symbol.upper()}
Current Price: ${current_price}
Previous Close: ${prev_close}
Market Cap: {market_cap_str}
P/E Ratio: {pe_ratio}
Company: {info.get('longName', 'N/A')}
"""
    except Exception as e:
        logger.error(f"Error fetching stock data: {e}")
        return f"Error fetching stock data for {symbol}: {str(e)}"

@tool
def get_stock_history(symbol: str, period: str = "1mo") -> str:
    """Get historical stock data and calculate key metrics.
    
    Args:
        symbol: Stock ticker symbol
        period: Time period - '1d', '5d', '1mo', '3mo', '6mo', '1y', '2y', '5y'
    """
    logger.info(f"📊 Quantitative Agent: Getting history for '{symbol}' ({period})")
    try:
        import yfinance as yf
        import pandas as pd
        
        ticker = yf.Ticker(symbol)
        hist = ticker.history(period=period)
        
        if hist.empty:
            return f"No historical data available for {symbol}"
        
        # Calculate metrics
        start_price = hist['Close'].iloc[0]
        end_price = hist['Close'].iloc[-1]
        high = hist['High'].max()
        low = hist['Low'].min()
        avg_volume = hist['Volume'].mean()
        pct_change = ((end_price - start_price) / start_price) * 100
        volatility = hist['Close'].pct_change().std() * 100
        
        return f"""
Stock: {symbol.upper()} ({period} analysis)
─────────────────────────────
Period Start: ${start_price:.2f}
Period End: ${end_price:.2f}
Change: {pct_change:+.2f}%
─────────────────────────────
Period High: ${high:.2f}
Period Low: ${low:.2f}
Avg Daily Volume: {avg_volume:,.0f}
Daily Volatility: {volatility:.2f}%
"""
    except Exception as e:
        logger.error(f"Error fetching history: {e}")
        return f"Error fetching history for {symbol}: {str(e)}"

@tool
def calculate_metrics(numbers: List[float], operation: str) -> str:
    """Perform calculations on a list of numbers.
    
    Args:
        numbers: List of numbers to analyze
        operation: One of 'mean', 'sum', 'max', 'min', 'std', 'median'
    """
    logger.info(f"🔢 Quantitative Agent: Calculating {operation}")
    try:
        import statistics
        
        if operation == "mean":
            result = statistics.mean(numbers)
        elif operation == "sum":
            result = sum(numbers)
        elif operation == "max":
            result = max(numbers)
        elif operation == "min":
            result = min(numbers)
        elif operation == "std":
            result = statistics.stdev(numbers) if len(numbers) > 1 else 0
        elif operation == "median":
            result = statistics.median(numbers)
        else:
            return f"Unknown operation: {operation}"
        
        return f"{operation.upper()} of {numbers}: {result:.4f}"
    except Exception as e:
        return f"Calculation error: {str(e)}"

# ============================================================
# 🤖 AGENT DEFINITIONS
# ============================================================

# Initialize models for each agent
supervisor_model = ChatOpenAI(model="gpt-4o-mini", temperature=0)
research_model = ChatOpenAI(model="gpt-4o-mini", temperature=0)
quant_model = ChatOpenAI(model="gpt-4o-mini", temperature=0)
writer_model = ChatOpenAI(model="gpt-4o-mini", temperature=0.7)  # More creative for writing

# Tool executors for specialized agents
research_tools = [web_search, scrape_summary]
quant_tools = [get_stock_price, get_stock_history, calculate_metrics]

research_model_with_tools = research_model.bind_tools(research_tools)
quant_model_with_tools = quant_model.bind_tools(quant_tools)

research_executor = ToolExecutor(research_tools)
quant_executor = ToolExecutor(quant_tools)

# ============================================================
# 🎯 SUPERVISOR NODE (The Router)
# ============================================================

SUPERVISOR_SYSTEM_PROMPT = """You are a Supervisor Agent that routes tasks to specialized workers.
You NEVER call tools yourself. You only decide which worker should handle the task.

Your workers:
1. RESEARCH_AGENT: For web searches, finding facts, current events, news, general knowledge
2. QUANT_AGENT: For stock prices, financial analysis, calculations, numerical data
3. WRITER_AGENT: For formatting reports, summarizing findings, creating final responses

Based on the user's request, decide which agent should work next.
If the task is complete, respond with FINISH.

Respond with ONLY one of: RESEARCH_AGENT, QUANT_AGENT, WRITER_AGENT, or FINISH

Examples:
- "What's the stock price of Apple?" → QUANT_AGENT
- "Search for latest AI news" → RESEARCH_AGENT
- "Give me a report on Tesla" → RESEARCH_AGENT (needs research first)
- "Analyze GOOGL stock performance" → QUANT_AGENT
- "Format this into a nice report" → WRITER_AGENT
- Task complete, all info gathered → WRITER_AGENT (to format final answer)
"""

def supervisor_node(state: MultiAgentState) -> Dict[str, Any]:
    """Supervisor decides which agent should work next."""
    messages = state["messages"]
    research_results = state.get("research_results", "")
    quant_results = state.get("quantitative_results", "")
    
    # Build context for supervisor
    context = f"""
User Request: {messages[-1].content if messages else 'No message'}

Work completed so far:
- Research Results: {research_results if research_results else 'None yet'}
- Quantitative Results: {quant_results if quant_results else 'None yet'}

Decide which agent should work next, or FINISH if we have enough information.
If we have gathered sufficient information, send to WRITER_AGENT to format the final response.
"""
    
    supervisor_messages = [
        SystemMessage(content=SUPERVISOR_SYSTEM_PROMPT),
        HumanMessage(content=context)
    ]
    
    response = supervisor_model.invoke(supervisor_messages)
    decision = response.content.strip().upper()
    
    logger.info(f"🎯 Supervisor Decision: {decision}")
    
    # Map decision to next agent
    if "RESEARCH" in decision:
        next_agent = "research_agent"
    elif "QUANT" in decision:
        next_agent = "quant_agent"
    elif "WRITER" in decision:
        next_agent = "writer_agent"
    elif "FINISH" in decision:
        next_agent = "finish"
    else:
        # Default to writer if unclear
        next_agent = "writer_agent"
    
    return {"next_agent": next_agent}

# ============================================================
# 🔍 RESEARCH AGENT NODE
# ============================================================

RESEARCH_SYSTEM_PROMPT = """You are a Research Agent specialized in finding information.
You have access to web search and scraping tools.
Your job is to gather factual information about the user's topic.

Be thorough but concise. Focus on key facts and current information.
After gathering information, summarize your findings clearly."""

def research_agent_node(state: MultiAgentState) -> Dict[str, Any]:
    """Research agent gathers information from the web."""
    messages = state["messages"]
    user_query = messages[-1].content if messages else ""
    
    logger.info(f"🔍 Research Agent working on: {user_query[:50]}...")
    
    research_messages = [
        SystemMessage(content=RESEARCH_SYSTEM_PROMPT),
        HumanMessage(content=f"Research this topic and provide key findings: {user_query}")
    ]
    
    # Let the agent decide to use tools
    response = research_model_with_tools.invoke(research_messages)
    
    # Execute any tool calls
    results = []
    if hasattr(response, 'tool_calls') and response.tool_calls:
        for tool_call in response.tool_calls:
            action = ToolInvocation(
                tool=tool_call["name"],
                tool_input=tool_call["args"]
            )
            result = research_executor.invoke(action)
            results.append(f"{tool_call['name']}: {result}")
    
    # Combine results
    if results:
        findings = "\n".join(results)
    else:
        findings = response.content
    
    logger.info(f"🔍 Research Agent completed. Found {len(results)} results.")
    
    return {
        "research_results": findings,
        "messages": [AIMessage(content=f"[Research Agent] {findings}")]
    }

# ============================================================
# 📊 QUANTITATIVE AGENT NODE
# ============================================================

QUANT_SYSTEM_PROMPT = """You are a Quantitative Agent specialized in financial analysis.
You have access to stock data tools and calculation functions.
Your job is to provide accurate numerical analysis.

Focus on:
- Current stock prices and key metrics
- Historical performance analysis
- Relevant calculations

Be precise with numbers. Always use tools to get real data."""

def quant_agent_node(state: MultiAgentState) -> Dict[str, Any]:
    """Quantitative agent analyzes financial data."""
    messages = state["messages"]
    user_query = messages[-1].content if messages else ""
    
    logger.info(f"📊 Quantitative Agent working on: {user_query[:50]}...")
    
    quant_messages = [
        SystemMessage(content=QUANT_SYSTEM_PROMPT),
        HumanMessage(content=f"Analyze this and provide numerical data: {user_query}")
    ]
    
    # Let the agent decide to use tools
    response = quant_model_with_tools.invoke(quant_messages)
    
    # Execute any tool calls
    results = []
    if hasattr(response, 'tool_calls') and response.tool_calls:
        for tool_call in response.tool_calls:
            action = ToolInvocation(
                tool=tool_call["name"],
                tool_input=tool_call["args"]
            )
            result = quant_executor.invoke(action)
            results.append(result)
    
    # Combine results
    if results:
        findings = "\n".join(results)
    else:
        findings = response.content
    
    logger.info(f"📊 Quantitative Agent completed.")
    
    return {
        "quantitative_results": findings,
        "messages": [AIMessage(content=f"[Quantitative Agent] {findings}")]
    }

# ============================================================
# ✍️ WRITER AGENT NODE
# ============================================================

WRITER_SYSTEM_PROMPT = """You are a Writer Agent specialized in creating clear, professional reports.
You DO NOT have any tools. Your job is to synthesize information into a well-formatted response.

Guidelines:
- Create a clear, structured response
- Use bullet points and sections where appropriate
- Highlight key findings and insights
- Be concise but comprehensive
- If you have stock data, format it nicely
- End with a brief summary or recommendation if relevant"""

def writer_agent_node(state: MultiAgentState) -> Dict[str, Any]:
    """Writer agent formats the final response."""
    messages = state["messages"]
    user_query = messages[-1].content if messages else ""
    research = state.get("research_results", "")
    quant = state.get("quantitative_results", "")
    
    logger.info("✍️ Writer Agent formatting final response...")
    
    context = f"""
Original Request: {user_query}

Research Findings:
{research if research else "No research data available."}

Quantitative Analysis:
{quant if quant else "No quantitative data available."}

Create a well-formatted, professional response that addresses the user's original request.
Synthesize all available information into a coherent answer.
"""
    
    writer_messages = [
        SystemMessage(content=WRITER_SYSTEM_PROMPT),
        HumanMessage(content=context)
    ]
    
    response = writer_model.invoke(writer_messages)
    
    logger.info("✍️ Writer Agent completed.")
    
    return {
        "final_report": response.content,
        "task_complete": True,
        "messages": [AIMessage(content=response.content)]
    }

# ============================================================
# 🔀 ROUTING LOGIC
# ============================================================

def route_after_supervisor(state: MultiAgentState) -> str:
    """Route to the next agent based on supervisor's decision."""
    next_agent = state.get("next_agent", "finish")
    
    if next_agent == "research_agent":
        return "research_agent"
    elif next_agent == "quant_agent":
        return "quant_agent"
    elif next_agent == "writer_agent":
        return "writer_agent"
    else:
        return "finish"

def should_continue_after_worker(state: MultiAgentState) -> str:
    """After a worker completes, go back to supervisor or finish."""
    if state.get("task_complete", False):
        return "finish"
    return "supervisor"

# ============================================================
# 🏗️ BUILD THE MULTI-AGENT GRAPH
# ============================================================

def create_multi_agent_graph():
    """Creates the multi-agent supervisor graph."""
    
    workflow = StateGraph(MultiAgentState)
    
    # Add all nodes
    workflow.add_node("supervisor", supervisor_node)
    workflow.add_node("research_agent", research_agent_node)
    workflow.add_node("quant_agent", quant_agent_node)
    workflow.add_node("writer_agent", writer_agent_node)
    
    # Set entry point
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
    
    # Workers go back to supervisor (or finish if writer)
    workflow.add_conditional_edges(
        "research_agent",
        should_continue_after_worker,
        {
            "supervisor": "supervisor",
            "finish": END
        }
    )
    
    workflow.add_conditional_edges(
        "quant_agent",
        should_continue_after_worker,
        {
            "supervisor": "supervisor",
            "finish": END
        }
    )
    
    # Writer always finishes
    workflow.add_edge("writer_agent", END)
    
    return workflow.compile()

# Create the compiled graph
multi_agent_graph = create_multi_agent_graph()

# ============================================================
# 🚀 PUBLIC API
# ============================================================

async def run_multi_agent(query: str) -> Dict[str, Any]:
    """
    Run a query through the multi-agent supervisor system.
    
    Args:
        query: The user's question or request
        
    Returns:
        Dict with answer and agent trace
    """
    logger.info(f"🚀 Starting Multi-Agent System for: {query[:50]}...")
    
    initial_state: MultiAgentState = {
        "messages": [HumanMessage(content=query)],
        "next_agent": "",
        "research_results": "",
        "quantitative_results": "",
        "final_report": "",
        "task_complete": False
    }
    
    try:
        # Run the graph
        final_state = multi_agent_graph.invoke(initial_state)
        
        # Extract the final answer
        answer = final_state.get("final_report", "")
        if not answer and final_state.get("messages"):
            # Fallback to last message
            answer = final_state["messages"][-1].content
        
        # Build agent trace for observability
        agent_trace = {
            "research_results": final_state.get("research_results", ""),
            "quantitative_results": final_state.get("quantitative_results", ""),
            "agents_used": []
        }
        
        if final_state.get("research_results"):
            agent_trace["agents_used"].append("Research Agent")
        if final_state.get("quantitative_results"):
            agent_trace["agents_used"].append("Quantitative Agent")
        agent_trace["agents_used"].append("Writer Agent")
        
        logger.info(f"✅ Multi-Agent completed. Agents used: {agent_trace['agents_used']}")
        
        return {
            "answer": answer,
            "agent_trace": agent_trace,
            "success": True
        }
        
    except Exception as e:
        logger.error(f"❌ Multi-Agent error: {str(e)}")
        return {
            "answer": f"Error processing request: {str(e)}",
            "agent_trace": {"error": str(e)},
            "success": False
        }


# ============================================================
# 🧪 TEST FUNCTION
# ============================================================

if __name__ == "__main__":
    import asyncio
    
    async def test():
        # Test 1: Stock analysis (should use Quant Agent)
        print("\n" + "="*60)
        print("TEST 1: Stock Analysis")
        print("="*60)
        result = await run_multi_agent("What is the current stock price of Apple (AAPL) and how has it performed in the last month?")
        print(f"Answer:\n{result['answer']}")
        print(f"Agents used: {result['agent_trace'].get('agents_used', [])}")
        
        # Test 2: Research query (should use Research Agent)
        print("\n" + "="*60)
        print("TEST 2: Research Query")
        print("="*60)
        result = await run_multi_agent("What are the latest developments in artificial intelligence?")
        print(f"Answer:\n{result['answer']}")
        print(f"Agents used: {result['agent_trace'].get('agents_used', [])}")
    
    asyncio.run(test())
