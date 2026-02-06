# Semantic Caching - Enterprise Optimization

## The Problem

LLMs are slow and expensive. If 50 users ask "What is the generic strategy for the stock market today?", you are paying OpenAI 50 times for the same answer.

**Without caching:**
- 50 identical questions = 50 LLM calls
- Latency: ~2000ms per call
- Cost: ~$1.50 (at $0.03/call)

## The Solution: Semantic Cache

Instead of exact string matching, Semantic Cache uses **vector similarity** to find semantically similar queries that have been answered recently.

**With caching:**
- 50 similar questions = 1 LLM call + 49 cache hits
- Cache hit latency: ~5ms
- Cost: ~$0.03 (98% savings!)

## How It Works

```
User Query: "How is Apple doing?"
         ↓
   [Generate Embedding]
         ↓
   [Check Vector Store]
         ↓
    ┌────┴────┐
    │         │
  HIT       MISS
    │         │
    ↓         ↓
 Return    Call LLM
 Cached    Execute
 Response  Tools
    │         │
    │         ↓
    │     Store in
    │      Cache
    │         │
    └────┬────┘
         ↓
   [Return Response]
```

### Semantic Matching Example

These queries would all share the same cached response:

| Query | Similarity |
|-------|-----------|
| "How is Apple doing?" | 1.000 (original) |
| "What's Apple's stock status?" | 0.95 |
| "Apple stock price today" | 0.93 |
| "Show me AAPL performance" | 0.91 |

All queries with similarity > 0.92 (configurable) return the cached response.

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                     FastAPI Server                       │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  /api/multi-agent                                        │
│       │                                                  │
│       ▼                                                  │
│  ┌──────────────┐    Hit    ┌─────────────────────┐    │
│  │   Semantic   │ ────────► │   Return Cached     │    │
│  │    Cache     │           │     Response        │    │
│  └──────┬───────┘           └─────────────────────┘    │
│         │ Miss                                          │
│         ▼                                               │
│  ┌──────────────┐                                       │
│  │  Multi-Agent │                                       │
│  │  Supervisor  │                                       │
│  └──────┬───────┘                                       │
│         │                                               │
│         ▼                                               │
│  ┌──────────────┐                                       │
│  │   Store in   │                                       │
│  │    Cache     │                                       │
│  └──────────────┘                                       │
│                                                          │
└─────────────────────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────┐
│              PostgreSQL + pgvector                       │
│                                                          │
│  semantic_cache table:                                   │
│  ┌─────────────────────────────────────────────────┐   │
│  │ query_hash | query_embedding | response | ttl    │   │
│  │ sha256     | vector(1536)    | text     | 5min   │   │
│  └─────────────────────────────────────────────────┘   │
│                                                          │
│  Vector Similarity Search:                               │
│  1 - (embedding <=> query_embedding) > 0.92             │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

## Tech Stack

- **Embeddings**: OpenAI `text-embedding-3-small` (1536 dimensions)
- **Vector Store**: PostgreSQL with pgvector extension
- **Similarity**: Cosine similarity via `<=>` operator
- **Index**: IVFFlat for fast approximate nearest neighbor search

## API Endpoints

### Multi-Agent with Caching
```http
POST /api/multi-agent
Content-Type: application/json

{
    "query": "What is Apple's stock price?"
}
```

Response includes cache metadata:
```json
{
    "answer": "Apple (AAPL) is currently trading at...",
    "agents_used": ["cache"],  // "cache" if hit, or actual agents
    "cache_hit": true,
    "cache_similarity": 0.95,
    "latency_ms": 5.2
}
```

### Cache Statistics
```http
GET /api/cache/stats
```

Response:
```json
{
    "enabled": true,
    "config": {
        "ttl_seconds": 300,
        "similarity_threshold": 0.92,
        "max_cache_size": 10000
    },
    "stats": {
        "total_queries": 1250,
        "cache_hits": 875,
        "cache_misses": 375,
        "hit_rate_percent": 70.0,
        "estimated_cost_saved_usd": 26.25,
        "avg_hit_latency_ms": 5.2,
        "avg_miss_latency_ms": 2150.3
    }
}
```

### Cache Entries
```http
GET /api/cache/entries?limit=50
```

### Configure Cache
```http
POST /api/cache/config
Content-Type: application/json

{
    "enabled": true,
    "ttl_seconds": 600,
    "similarity_threshold": 0.90
}
```

### Invalidate Cache
```http
DELETE /api/cache                    # Clear all
DELETE /api/cache?query=Apple stock  # Clear specific
```

## Configuration

Environment variables:

```env
# Enable/disable semantic caching
SEMANTIC_CACHE_ENABLED=true

# Time-to-live in seconds (default: 300 = 5 minutes)
SEMANTIC_CACHE_TTL=300

# Similarity threshold for cache hit (default: 0.92)
SEMANTIC_CACHE_THRESHOLD=0.92
```

## Best Practices

### 1. TTL Strategy

| Use Case | Recommended TTL |
|----------|-----------------|
| Stock prices | 1-5 minutes |
| News queries | 15-30 minutes |
| General knowledge | 1-24 hours |
| Static FAQs | 24+ hours |

### 2. Similarity Threshold

| Threshold | Behavior |
|-----------|----------|
| 0.95+ | Very strict - only near-identical queries |
| 0.90-0.95 | Balanced - similar intent |
| 0.85-0.90 | Lenient - broader matching |
| <0.85 | Not recommended - too many false positives |

### 3. Cache Invalidation

- Invalidate when underlying data changes
- Set appropriate TTL for time-sensitive data
- Monitor hit rate - too low suggests threshold is too high

## Monitoring

Watch these metrics:

1. **Hit Rate**: Target 60-80% for most applications
2. **Latency Reduction**: Cache hits should be <10ms vs ~2000ms for LLM
3. **Cost Savings**: Track `estimated_cost_saved_usd`
4. **Cache Size**: Ensure not exceeding `max_cache_size`

## Example Cost Savings

For an application with 10,000 daily queries:

| Metric | Without Cache | With Cache (70% hit rate) |
|--------|---------------|--------------------------|
| LLM Calls | 10,000 | 3,000 |
| Cost/day | $300 | $90 |
| Monthly Savings | - | **$6,300** |

## Troubleshooting

### Low Hit Rate
- Lower similarity threshold (0.92 → 0.88)
- Increase TTL
- Analyze cache misses for patterns

### High Latency on Hits
- Check PostgreSQL performance
- Ensure pgvector index exists
- Consider HNSW index for larger datasets

### Stale Responses
- Reduce TTL
- Implement manual invalidation for critical updates
- Add cache-busting headers in frontend
