"""
Semantic Cache for Enterprise RAG Platform

This module implements semantic caching to reduce LLM costs and latency.
Instead of exact string matching, it uses vector similarity to find
semantically similar queries that have been answered recently.

Example:
    - Query 1: "How is Apple doing?" -> Cache Miss -> LLM Response -> Store
    - Query 2: "What's the status of Apple stock?" -> Cache Hit (similar) -> Return cached

Tech: pgvector for vector similarity search, OpenAI embeddings for query vectorization.
"""

import os
import json
import hashlib
import asyncio
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List, Tuple
from dataclasses import dataclass
from enum import Enum

import psycopg
from psycopg.rows import dict_row
from openai import OpenAI


class CacheStatus(Enum):
    HIT = "hit"
    MISS = "miss"
    EXPIRED = "expired"
    DISABLED = "disabled"


@dataclass
class CacheResult:
    """Result from cache lookup."""
    status: CacheStatus
    query: str
    response: Optional[str] = None
    cached_query: Optional[str] = None
    similarity: Optional[float] = None
    latency_ms: Optional[float] = None
    cost_saved: Optional[float] = None


@dataclass
class CacheStats:
    """Cache statistics."""
    total_queries: int
    cache_hits: int
    cache_misses: int
    hit_rate: float
    estimated_cost_saved: float
    avg_hit_latency_ms: float
    avg_miss_latency_ms: float


class SemanticCache:
    """
    Semantic Cache using pgvector for similarity search.
    
    Features:
    - Vector similarity search for semantic matching
    - Configurable TTL (time-to-live) for cache entries
    - Adjustable similarity threshold
    - Cache statistics and monitoring
    - Thread-safe async operations
    """
    
    # Estimated cost per LLM call (GPT-4 average)
    ESTIMATED_COST_PER_CALL = 0.03  # $0.03 average
    
    def __init__(
        self,
        database_url: str,
        embedding_model: str = "text-embedding-3-small",
        similarity_threshold: float = 0.92,
        ttl_seconds: int = 300,  # 5 minutes default
        enabled: bool = True,
        max_cache_size: int = 10000
    ):
        """
        Initialize the Semantic Cache.
        
        Args:
            database_url: PostgreSQL connection string
            embedding_model: OpenAI embedding model to use
            similarity_threshold: Minimum similarity for cache hit (0-1)
            ttl_seconds: Time-to-live for cache entries in seconds
            enabled: Whether caching is enabled
            max_cache_size: Maximum number of entries to keep
        """
        self.database_url = database_url
        self.embedding_model = embedding_model
        self.similarity_threshold = similarity_threshold
        self.ttl_seconds = ttl_seconds
        self.enabled = enabled
        self.max_cache_size = max_cache_size
        
        # Initialize OpenAI client for embeddings
        self.openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        
        # Statistics
        self._stats = {
            "total_queries": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "total_hit_latency_ms": 0,
            "total_miss_latency_ms": 0
        }
        
        # Embedding dimension for text-embedding-3-small
        self.embedding_dim = 1536
        
    async def initialize(self):
        """Initialize the cache table in PostgreSQL."""
        async with await psycopg.AsyncConnection.connect(self.database_url) as conn:
            async with conn.cursor() as cur:
                # Ensure pgvector extension is enabled
                await cur.execute("CREATE EXTENSION IF NOT EXISTS vector")
                
                # Create semantic cache table
                await cur.execute(f"""
                    CREATE TABLE IF NOT EXISTS semantic_cache (
                        id SERIAL PRIMARY KEY,
                        query_hash VARCHAR(64) UNIQUE NOT NULL,
                        query_text TEXT NOT NULL,
                        query_embedding vector({self.embedding_dim}),
                        response_text TEXT NOT NULL,
                        response_metadata JSONB DEFAULT '{{}}',
                        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                        expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
                        hit_count INTEGER DEFAULT 0,
                        last_hit_at TIMESTAMP WITH TIME ZONE
                    )
                """)
                
                # Create index for vector similarity search
                await cur.execute("""
                    CREATE INDEX IF NOT EXISTS idx_semantic_cache_embedding 
                    ON semantic_cache 
                    USING ivfflat (query_embedding vector_cosine_ops)
                    WITH (lists = 100)
                """)
                
                # Create index for expiration cleanup
                await cur.execute("""
                    CREATE INDEX IF NOT EXISTS idx_semantic_cache_expires 
                    ON semantic_cache (expires_at)
                """)
                
                await conn.commit()
                
        print("✅ Semantic cache initialized")
    
    def _get_embedding(self, text: str) -> List[float]:
        """Generate embedding for a text query."""
        response = self.openai_client.embeddings.create(
            model=self.embedding_model,
            input=text
        )
        return response.data[0].embedding
    
    def _hash_query(self, query: str) -> str:
        """Generate a hash for exact query matching."""
        return hashlib.sha256(query.lower().strip().encode()).hexdigest()
    
    async def get(self, query: str) -> CacheResult:
        """
        Look up a query in the semantic cache.
        
        Args:
            query: The user's query
            
        Returns:
            CacheResult with status and optional cached response
        """
        import time
        start_time = time.time()
        
        self._stats["total_queries"] += 1
        
        if not self.enabled:
            return CacheResult(
                status=CacheStatus.DISABLED,
                query=query
            )
        
        try:
            # Generate embedding for the query
            query_embedding = self._get_embedding(query)
            
            async with await psycopg.AsyncConnection.connect(self.database_url) as conn:
                async with conn.cursor(row_factory=dict_row) as cur:
                    # First try exact match (faster)
                    query_hash = self._hash_query(query)
                    await cur.execute("""
                        SELECT query_text, response_text, response_metadata,
                               1.0 as similarity, expires_at
                        FROM semantic_cache
                        WHERE query_hash = %s AND expires_at > NOW()
                    """, (query_hash,))
                    
                    result = await cur.fetchone()
                    
                    if result:
                        # Exact match found
                        latency_ms = (time.time() - start_time) * 1000
                        self._stats["cache_hits"] += 1
                        self._stats["total_hit_latency_ms"] += latency_ms
                        
                        # Update hit count
                        await cur.execute("""
                            UPDATE semantic_cache 
                            SET hit_count = hit_count + 1, last_hit_at = NOW()
                            WHERE query_hash = %s
                        """, (query_hash,))
                        await conn.commit()
                        
                        return CacheResult(
                            status=CacheStatus.HIT,
                            query=query,
                            response=result["response_text"],
                            cached_query=result["query_text"],
                            similarity=1.0,
                            latency_ms=latency_ms,
                            cost_saved=self.ESTIMATED_COST_PER_CALL
                        )
                    
                    # Semantic similarity search
                    embedding_str = "[" + ",".join(map(str, query_embedding)) + "]"
                    await cur.execute(f"""
                        SELECT query_text, response_text, response_metadata,
                               1 - (query_embedding <=> %s::vector) as similarity,
                               expires_at
                        FROM semantic_cache
                        WHERE expires_at > NOW()
                        ORDER BY query_embedding <=> %s::vector
                        LIMIT 1
                    """, (embedding_str, embedding_str))
                    
                    result = await cur.fetchone()
                    
                    if result and result["similarity"] >= self.similarity_threshold:
                        # Semantic match found
                        latency_ms = (time.time() - start_time) * 1000
                        self._stats["cache_hits"] += 1
                        self._stats["total_hit_latency_ms"] += latency_ms
                        
                        # Update hit count on the matched entry
                        await cur.execute("""
                            UPDATE semantic_cache 
                            SET hit_count = hit_count + 1, last_hit_at = NOW()
                            WHERE query_text = %s
                        """, (result["query_text"],))
                        await conn.commit()
                        
                        return CacheResult(
                            status=CacheStatus.HIT,
                            query=query,
                            response=result["response_text"],
                            cached_query=result["query_text"],
                            similarity=float(result["similarity"]),
                            latency_ms=latency_ms,
                            cost_saved=self.ESTIMATED_COST_PER_CALL
                        )
                    
                    # Cache miss
                    latency_ms = (time.time() - start_time) * 1000
                    self._stats["cache_misses"] += 1
                    self._stats["total_miss_latency_ms"] += latency_ms
                    
                    return CacheResult(
                        status=CacheStatus.MISS,
                        query=query,
                        similarity=float(result["similarity"]) if result else 0.0,
                        latency_ms=latency_ms
                    )
                    
        except Exception as e:
            print(f"⚠️ Cache lookup error: {e}")
            self._stats["cache_misses"] += 1
            return CacheResult(
                status=CacheStatus.MISS,
                query=query
            )
    
    async def set(
        self,
        query: str,
        response: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Store a query-response pair in the cache.
        
        Args:
            query: The original query
            response: The generated response
            metadata: Optional metadata about the response
            
        Returns:
            True if successfully cached, False otherwise
        """
        if not self.enabled:
            return False
            
        try:
            query_hash = self._hash_query(query)
            query_embedding = self._get_embedding(query)
            embedding_str = "[" + ",".join(map(str, query_embedding)) + "]"
            expires_at = datetime.utcnow() + timedelta(seconds=self.ttl_seconds)
            
            async with await psycopg.AsyncConnection.connect(self.database_url) as conn:
                async with conn.cursor() as cur:
                    # Upsert the cache entry
                    await cur.execute("""
                        INSERT INTO semantic_cache 
                            (query_hash, query_text, query_embedding, response_text, 
                             response_metadata, expires_at)
                        VALUES (%s, %s, %s::vector, %s, %s, %s)
                        ON CONFLICT (query_hash) DO UPDATE SET
                            response_text = EXCLUDED.response_text,
                            response_metadata = EXCLUDED.response_metadata,
                            expires_at = EXCLUDED.expires_at,
                            created_at = NOW()
                    """, (
                        query_hash,
                        query,
                        embedding_str,
                        response,
                        json.dumps(metadata or {}),
                        expires_at
                    ))
                    
                    await conn.commit()
                    
            # Cleanup old entries if needed
            await self._cleanup_if_needed()
            
            return True
            
        except Exception as e:
            print(f"⚠️ Cache set error: {e}")
            return False
    
    async def _cleanup_if_needed(self):
        """Remove expired entries and enforce max cache size."""
        try:
            async with await psycopg.AsyncConnection.connect(self.database_url) as conn:
                async with conn.cursor() as cur:
                    # Remove expired entries
                    await cur.execute("""
                        DELETE FROM semantic_cache WHERE expires_at < NOW()
                    """)
                    
                    # Check total count
                    await cur.execute("SELECT COUNT(*) FROM semantic_cache")
                    count = (await cur.fetchone())[0]
                    
                    # If over limit, remove least recently used entries
                    if count > self.max_cache_size:
                        excess = count - self.max_cache_size
                        await cur.execute("""
                            DELETE FROM semantic_cache
                            WHERE id IN (
                                SELECT id FROM semantic_cache
                                ORDER BY COALESCE(last_hit_at, created_at) ASC
                                LIMIT %s
                            )
                        """, (excess,))
                    
                    await conn.commit()
                    
        except Exception as e:
            print(f"⚠️ Cache cleanup error: {e}")
    
    async def invalidate(self, query: Optional[str] = None) -> int:
        """
        Invalidate cache entries.
        
        Args:
            query: Specific query to invalidate, or None for all
            
        Returns:
            Number of entries invalidated
        """
        try:
            async with await psycopg.AsyncConnection.connect(self.database_url) as conn:
                async with conn.cursor() as cur:
                    if query:
                        query_hash = self._hash_query(query)
                        await cur.execute("""
                            DELETE FROM semantic_cache WHERE query_hash = %s
                        """, (query_hash,))
                    else:
                        await cur.execute("DELETE FROM semantic_cache")
                    
                    count = cur.rowcount
                    await conn.commit()
                    return count
                    
        except Exception as e:
            print(f"⚠️ Cache invalidate error: {e}")
            return 0
    
    async def get_stats(self) -> CacheStats:
        """Get cache statistics."""
        total = self._stats["total_queries"]
        hits = self._stats["cache_hits"]
        misses = self._stats["cache_misses"]
        
        hit_rate = (hits / total * 100) if total > 0 else 0
        cost_saved = hits * self.ESTIMATED_COST_PER_CALL
        
        avg_hit_latency = (
            self._stats["total_hit_latency_ms"] / hits if hits > 0 else 0
        )
        avg_miss_latency = (
            self._stats["total_miss_latency_ms"] / misses if misses > 0 else 0
        )
        
        return CacheStats(
            total_queries=total,
            cache_hits=hits,
            cache_misses=misses,
            hit_rate=hit_rate,
            estimated_cost_saved=cost_saved,
            avg_hit_latency_ms=avg_hit_latency,
            avg_miss_latency_ms=avg_miss_latency
        )
    
    async def get_cache_entries(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get recent cache entries for monitoring."""
        try:
            async with await psycopg.AsyncConnection.connect(self.database_url) as conn:
                async with conn.cursor(row_factory=dict_row) as cur:
                    await cur.execute("""
                        SELECT id, query_text, 
                               LEFT(response_text, 200) as response_preview,
                               hit_count, created_at, expires_at, last_hit_at
                        FROM semantic_cache
                        ORDER BY created_at DESC
                        LIMIT %s
                    """, (limit,))
                    
                    results = await cur.fetchall()
                    return [dict(r) for r in results]
                    
        except Exception as e:
            print(f"⚠️ Cache entries fetch error: {e}")
            return []
    
    def set_threshold(self, threshold: float):
        """Update similarity threshold (0-1)."""
        if 0 <= threshold <= 1:
            self.similarity_threshold = threshold
            
    def set_ttl(self, ttl_seconds: int):
        """Update TTL in seconds."""
        if ttl_seconds > 0:
            self.ttl_seconds = ttl_seconds
            
    def enable(self):
        """Enable caching."""
        self.enabled = True
        
    def disable(self):
        """Disable caching."""
        self.enabled = False


# Singleton instance
_cache_instance: Optional[SemanticCache] = None


def get_semantic_cache() -> Optional[SemanticCache]:
    """Get the singleton cache instance."""
    return _cache_instance


async def initialize_semantic_cache(
    database_url: str,
    **kwargs
) -> SemanticCache:
    """
    Initialize the global semantic cache instance.
    
    Args:
        database_url: PostgreSQL connection string
        **kwargs: Additional arguments for SemanticCache
        
    Returns:
        Initialized SemanticCache instance
    """
    global _cache_instance
    
    _cache_instance = SemanticCache(database_url, **kwargs)
    await _cache_instance.initialize()
    
    return _cache_instance
