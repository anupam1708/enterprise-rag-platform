-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Create vector_store table if it doesn't exist
CREATE TABLE IF NOT EXISTS vector_store (
    id uuid PRIMARY KEY,
    content text,
    metadata json,
    embedding vector(1536)
);

-- Create index for faster similarity search
CREATE INDEX IF NOT EXISTS vector_store_embedding_idx 
ON vector_store USING hnsw (embedding vector_cosine_ops);

-- Create users table
CREATE TABLE IF NOT EXISTS users (
    id BIGSERIAL PRIMARY KEY,
    username VARCHAR(255) NOT NULL UNIQUE,
    email VARCHAR(255) NOT NULL UNIQUE,
    password VARCHAR(255) NOT NULL,
    role VARCHAR(50) NOT NULL DEFAULT 'USER',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    enabled BOOLEAN NOT NULL DEFAULT TRUE
);

-- Create chat_audit_logs table
CREATE TABLE IF NOT EXISTS chat_audit_logs (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT,
    session_id VARCHAR(255),
    query_text TEXT NOT NULL,
    response_text TEXT,
    timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    response_time_ms BIGINT,
    pii_detected BOOLEAN DEFAULT FALSE,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
);

-- ============================================================
-- LangGraph State Persistence Tables (Production-Grade)
-- ============================================================
-- These tables enable "Time Travel" - rewinding to any point in
-- the conversation graph and resuming from there, even after restarts.

-- Main checkpoints table: stores the full state snapshot at each step
CREATE TABLE IF NOT EXISTS checkpoints (
    thread_id TEXT NOT NULL,
    checkpoint_ns TEXT NOT NULL DEFAULT '',
    checkpoint_id TEXT NOT NULL,
    parent_checkpoint_id TEXT,
    type TEXT,
    checkpoint JSONB NOT NULL,
    metadata JSONB NOT NULL DEFAULT '{}',
    PRIMARY KEY (thread_id, checkpoint_ns, checkpoint_id)
);

-- Writes table: stores pending writes that will be applied to the next checkpoint
CREATE TABLE IF NOT EXISTS checkpoint_writes (
    thread_id TEXT NOT NULL,
    checkpoint_ns TEXT NOT NULL DEFAULT '',
    checkpoint_id TEXT NOT NULL,
    task_id TEXT NOT NULL,
    idx INTEGER NOT NULL,
    channel TEXT NOT NULL,
    type TEXT,
    value JSONB,
    PRIMARY KEY (thread_id, checkpoint_ns, checkpoint_id, task_id, idx)
);

-- Indexes for efficient querying and time-travel operations
CREATE INDEX IF NOT EXISTS idx_checkpoints_thread_id ON checkpoints(thread_id, checkpoint_id);
CREATE INDEX IF NOT EXISTS idx_checkpoint_writes_thread_id ON checkpoint_writes(thread_id, checkpoint_id);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_chat_audit_logs_user_id ON chat_audit_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_chat_audit_logs_session_id ON chat_audit_logs(session_id);
CREATE INDEX IF NOT EXISTS idx_chat_audit_logs_timestamp ON chat_audit_logs(timestamp);

-- ============================================================
-- Semantic Cache Table (Enterprise Optimization)
-- ============================================================
-- Stores query embeddings and responses for semantic similarity matching.
-- Reduces LLM costs and latency by reusing answers for similar questions.
-- Example: "How is Apple doing?" and "What's Apple's stock status?" can share a response.

CREATE TABLE IF NOT EXISTS semantic_cache (
    id SERIAL PRIMARY KEY,
    query_hash VARCHAR(64) UNIQUE NOT NULL,
    query_text TEXT NOT NULL,
    query_embedding vector(1536),
    response_text TEXT NOT NULL,
    response_metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    hit_count INTEGER DEFAULT 0,
    last_hit_at TIMESTAMP WITH TIME ZONE
);

-- Index for vector similarity search using IVFFlat
-- Uses cosine similarity for semantic matching
CREATE INDEX IF NOT EXISTS idx_semantic_cache_embedding 
ON semantic_cache 
USING ivfflat (query_embedding vector_cosine_ops)
WITH (lists = 100);

-- Index for expiration cleanup
CREATE INDEX IF NOT EXISTS idx_semantic_cache_expires 
ON semantic_cache (expires_at);

-- Index for exact query hash lookup
CREATE INDEX IF NOT EXISTS idx_semantic_cache_hash
ON semantic_cache (query_hash);
