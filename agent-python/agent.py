from datetime import datetime
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain.tools import tool
from langchain.agents import create_tool_calling_agent, AgentExecutor
from langchain_core.prompts import ChatPromptTemplate
from langchain_community.tools import DuckDuckGoSearchRun # <--- 1. Import this

# 1. Setup
load_dotenv()
llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

# 2. Define Tools (The "Actions")
# The docstring is CRITICAL. The AI reads it to know WHEN to use this tool.

# Initialize the Search Tool
search = DuckDuckGoSearchRun()

@tool
def get_current_time():
    """Returns the current date and time."""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

@tool
def count_letters(text: str):
    """Returns the length of a word or sentence."""
    return len(text)

@tool
def web_search(query: str):
    """Search the internet for real-time information, current prices, latest news, weather, sports scores, stock/crypto prices, or any facts that change frequently. Use this tool whenever you need up-to-date information that you don't already know."""
    return search.run(query)

tools = [get_current_time, count_letters, web_search]

# 3. Create the Prompt
prompt = ChatPromptTemplate.from_messages([
    ("system", "You are a helpful assistant. You have access to tools."),
    ("human", "{input}"),
    ("placeholder", "{agent_scratchpad}"),
])

# 4. Create the Agent
agent = create_tool_calling_agent(llm, tools, prompt)
agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True)

# 5. Helper function to run it
def run_agent(query: str):
    result = agent_executor.invoke({"input": query})
    return result["output"]