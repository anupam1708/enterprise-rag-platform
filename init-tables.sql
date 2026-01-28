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

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_chat_audit_logs_user_id ON chat_audit_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_chat_audit_logs_session_id ON chat_audit_logs(session_id);
CREATE INDEX IF NOT EXISTS idx_chat_audit_logs_timestamp ON chat_audit_logs(timestamp);
