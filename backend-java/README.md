# Enterprise Compliance RAG System 🛡️

A production-ready Retrieval-Augmented Generation (RAG) system designed for highly regulated industries (Finance/Healthcare). It features a secure Java Spring Boot backend with built-in PII masking, audit logging, and role-based guardrails.

## 🏗️ Architecture



* **Backend:** Java 17, Spring Boot 3.2, Spring AI
* **Vector Database:** PostgreSQL + `pgvector`
* **AI Model:** OpenAI GPT-4 (via API)
* **Security:** AOP-based PII Guardrails (Regex & Pattern Matching)

## 🚀 Key Features

### 1. Secure Ingestion Pipeline
* Parses PDF documents and chunks text based on semantic meaning (TokenTextSplitter).
* Stores vector embeddings in PostgreSQL using the HNSW index for low-latency retrieval.

### 2. Privacy-First "Guardrails" (AOP)
* Implements Aspect-Oriented Programming (AOP) to intercept all user queries *before* they touch the LLM.
* **Automatic Redaction:** Detects and masks sensitive data (Emails, Phone Numbers, SSNs).
    * *Input:* "My phone number is 555-0199..."
    * *LLM Receives:* "My phone number is [REDACTED PHONE]..."

### 3. Audit Trails
* Every interaction is logged to a persistent audit table (`chat_audit_logs`).
* Tracks the sanitized query, timestamp, and AI response for compliance reporting.

## 🛠️ Getting Started

### Prerequisites
* Java 17+
* Docker (for PostgreSQL)
* OpenAI API Key

### Setup
1.  **Start Database:**
    ```bash
    docker run --name pgvector -e POSTGRES_PASSWORD=password -p 5432:5432 -d pgvector/pgvector:pg16
    ```
2.  **Configure Environment:**
    Rename `application.properties.example` to `application.properties` and add your API Key.
3.  **Run Application:**
    ```bash
    ./mvnw spring-boot:run
    ```

## 🧪 API Endpoints

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `POST` | `/api/ingest` | Upload a PDF file to the knowledge base. |
| `GET` | `/api/chat?query=...` | Ask a question (Auto-sanitized). |

## 📜 License
MIT