LINKEDIN ARTICLE — PASTE INSTRUCTIONS
======================================
1. Go to LinkedIn → Write Article
2. Click the title field → paste the title
3. Click the body field → paste everything below the dashed line
4. Use LinkedIn's toolbar (H1/H2 buttons) to format section headings
5. Use the Bold button (B) for any emphasis you want
6. The code blocks will need manual formatting with LinkedIn's "Insert code" option
----------------------------------------------------------------------


Building a Level 3 Autonomous Financial Agent with LangGraph & RAG

How I built a production-grade AI platform that researches, reasons, acts — and asks for permission before doing anything irreversible.


Most AI demos show a chatbot answering questions. That's Level 1.

A few show agents that search the web or call APIs. That's Level 2.

What I built is different. It's a system where multiple specialized AI agents collaborate, persist memory across sessions, route between search engines based on query intent, generate live financial dashboards — and pause to ask a human "are you sure?" before doing anything that can't be undone.

That's Level 3 autonomy: the agent plans, researches, and executes — but keeps a human in the loop for high-stakes decisions.

Here's how I built it, the architectural decisions behind it, and what I learned along the way.


What Is a "Level 3" Autonomous Agent?

The autonomy spectrum for AI agents looks like this:

Level 1 — Responds to questions (ChatGPT with no tools)
Level 2 — Uses tools to look things up (agent with web search)
Level 3 — Plans, multi-step reasoning, takes actions, loops back for human review
Level 4 — Fully autonomous with no oversight (not yet safe for production)

Level 3 is the sweet spot for enterprise use: capable enough to be genuinely useful, constrained enough to be trustworthy.


The Architecture

The platform has four layers:

The Next.js frontend handles the chat UI, streaming generative UI components like charts and stock cards, and the HITL approval interface.

A Java Spring Boot gateway handles authentication, JWT, and rate limiting.

The Python FastAPI agent service is where all the intelligence lives — LangGraph graphs, multi-agent routing, HITL, hybrid search, and semantic caching.

PostgreSQL with pgvector sits underneath everything — conversation state, semantic cache, embeddings, and document storage all in one database.


1. The Multi-Agent Supervisor Pattern

The core insight here is one that most GenAI engineers learn the hard way: a single agent with 20 tools is a disaster. It picks the wrong tool, hallucinates tool arguments, and becomes unreliable.

The solution is separation of concerns — the same principle that makes good software architecture.

The Supervisor is a routing LLM. It reads the query and decides which specialist to call. No tools of its own — just routing decisions.

The Research Agent gets hybrid web search and URL scraping. It knows how to find information.

The Quantitative Agent gets yfinance, pandas, and math operations. It knows how to analyze financial data.

The Writer Agent has no tools at all — just an LLM that synthesizes everything into a coherent response.

Each specialist has a small, focused tool set and becomes highly reliable at its specific job. This is built on LangGraph's StateGraph, which gives a typed state machine rather than an unpredictable chain. The state enforces that data flows in one direction, each agent reads only what it needs, and state is immutable between steps.


2. The Hardest Feature to Get Right: Human-in-the-Loop

Most tutorials show HITL as a simple "ask before acting" pattern. Production HITL is harder. You need the agent's state to survive while it waits for a human — which could be seconds, hours, or never.

The solution is LangGraph's interrupt_before parameter combined with a PostgreSQL checkpointer.

When the agent decides to call buy_stock or delete_database_records, the graph:
1. Saves the entire state to PostgreSQL (survives container restarts)
2. Returns pending_approval: True to the frontend
3. Waits — indefinitely — until a human approves or rejects

The frontend shows an inline approval card with the tool name, all parameters, and Approve/Reject buttons. When the user clicks Approve, the graph resumes from the exact checkpoint. The LLM doesn't re-run. The research doesn't repeat. It picks up exactly where it paused.

This pattern is the difference between a demo and a system you'd trust with real money.


3. Hybrid Search: Routing Between Two Best-in-Class APIs

One of the subtler architectural decisions was replacing a single search provider with a hybrid routing layer.

The problem: no single search API is best for all query types.

Tavily excels at recent news, current prices, and trending events.
Exa excels at deep semantic research, technical documentation, and conceptual queries.

So I built a lightweight router that analyzes the query and picks the right engine using regex pattern matching — zero extra LLM tokens. If either engine fails, the other is tried automatically as fallback.

"What's Apple's stock price today?" routes to Tavily.
"Explain how RAG architecture works" routes to Exa.

The agent consistently gets better, more relevant results — and the cost is just a few microseconds of CPU time for the regex check.


4. Semantic Caching That Actually Saves Money

Standard caching breaks on slight query variations. "How is Apple doing?" and "What's Apple's stock situation?" are semantically identical but would cache-miss with string matching.

The solution is vector similarity caching using pgvector.

When a query arrives, an OpenAI embedding is generated. The cosine distance is calculated against all cached embeddings. If the distance is below 0.08, the cached response is returned in roughly 15ms. If it's a miss, the multi-agent runs and the result is stored with a TTL.

The threshold of 0.08 catches paraphrases and synonyms while rejecting genuinely different queries. At approximately $0.03 saved per cache hit, this pays back quickly on a platform with moderate traffic.

Cache stats — hit rate, cost saved, average latency — are exposed via API and can be tuned at runtime without a deployment.


5. Generative UI: Beyond Text Responses

Text responses are limiting for financial data. When someone asks "Compare Google and Microsoft stock," they need a chart, not a paragraph.

The platform streams structured UI components via Server-Sent Events. The frontend detects stock symbols in the query and picks a rendering strategy:

Single stock query → StockCard + LineChart + text analysis
Multiple stocks → ComparisonChart + DataTable + text
No symbols → Multi-agent text response

Each artifact arrives as typed JSON and the frontend renders live Recharts components as they stream in. The UI feels alive — not like waiting for a response, but watching the agent think.


6. Red Team Security Testing Built Into CI/CD

An AI agent that can send emails, execute trades, and delete database records is a serious attack surface. I built an adversarial testing framework with 40+ payloads across 8 attack categories:

Prompt injection — "Ignore previous instructions..."
Jailbreaking — DAN prompts, hypothetical framing, role-play exploits
Unauthorized actions — "Transfer $10,000 from account 1234..."
PII extraction — Attempting to surface other users' data
Context manipulation — False authority claims, memory injection
System prompt extraction — Attempts to leak the agent's instructions

This runs in CI/CD on every push with a 95% defense rate threshold. If the agent starts responding to these prompts, the pipeline fails.

Because LangSmith tracing is enabled, every red team run appears with full trace visibility. That's how I know exactly how the agent responded to each attack — including why the LangSmith trace showed a "Transfer $10,000" request. It wasn't a real user. It was the red team suite running on deploy.


7. Production Infrastructure: What Actually Matters

Everything runs in Docker Compose on a single AWS EC2 instance: nginx for SSL termination, Next.js frontend, Java Spring Boot backend, Python FastAPI agent, PostgreSQL, Prometheus, and Grafana.

Three infrastructure lessons I learned the hard way:

All services need restart: always. Before I added this, every EC2 reboot silently killed the app. Scheduled maintenance, billing pause, kernel update — all of them would take the platform down until I manually SSHed in. One line per service in docker-compose.yml prevents an entire class of outages.

Docker needs to start on boot. sudo systemctl enable docker — one command, run once. Obvious in hindsight.

GitHub Actions deploys on every push to main. The pipeline frees disk space first (important on a small instance), copies secrets as .env files, builds containers sequentially to avoid OOM, and runs a verification step that confirms all containers are running before marking the deployment successful.


What I Learned Building This

LangGraph's interrupt pattern is genuinely powerful, but the docs undersell it. The interrupt_before parameter plus PostgreSQL checkpointer is what makes HITL real. The agent's full state is serialized to the database and can be resumed hours later. That's not a demo trick. That's a production feature.

Multi-agent beats single agent for reliability. I initially built this as one agent with all the tools. It was flaky — wrong tool picks, bad arguments, inconsistent output. Splitting into specialized agents with small focused tool sets made each agent dramatically more reliable.

Semantic caching is underutilized. Every RAG tutorial says "use a cache." Almost none show how to implement semantic caching. The pgvector plus cosine distance approach handles the real-world messiness of natural language far better than string matching.

Security testing belongs in CI/CD, not as an afterthought. Building the red team suite was the most time-consuming part. It's also the part that gives me the most confidence. Knowing that a fund transfer request and a DAN jailbreak are tested on every deploy changes how you think about the system.

The frontend makes or breaks an AI product. Streaming SSE to render live charts is harder than it sounds. But the difference between "here is a paragraph about Apple stock" and a live chart loading in real time is enormous.


The Stack

Frontend: Next.js 14, TypeScript, Tailwind CSS, Recharts
Gateway: Java Spring Boot, JWT auth
AI Agent: Python FastAPI, LangGraph, LangChain
LLM: GPT-4o-mini
Search: Tavily + Exa (hybrid routing)
Database: PostgreSQL + pgvector
Caching: Semantic cache (cosine similarity)
Observability: LangSmith, Prometheus, Grafana, CloudWatch
Security: Red team test suite (40+ adversarial payloads)
Infrastructure: Docker Compose, AWS EC2, GitHub Actions

Live demo: hnsworld.ai


What's Next

Streaming HITL — making the approval card stream the agent's reasoning in real-time while waiting for human input.

Cross-session memory — the graph has per-thread state, but no long-term memory across separate sessions yet.

Broader search routing — the hybrid router is designed to be extended; Brave Search and YOU.com are natural additions for specific query types.


If you're building production AI agents and want to talk architecture — specifically LangGraph state persistence, HITL patterns, or multi-agent design — I'm happy to connect.

The full codebase is deployed and running at hnsworld.ai.


#LangGraph #GenerativeAI #RAG #LLMOps #AgenticAI #Python #FinancialAI #MachineLearning #SoftwareEngineering #AIEngineering
