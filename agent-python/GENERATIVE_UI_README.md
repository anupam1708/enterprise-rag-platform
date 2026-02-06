# Generative UI (Streaming Components)

## The Pattern

Traditional AI agents output plain text: `"Apple stock is $180..."`. This creates a poor user experience - no visual data, no interactivity.

**Generative UI** enables the agent to stream structured JSON "artifacts" that the frontend renders as rich, interactive UI components (charts, tables, cards) in real-time.

## Architecture

```
┌────────────────────────────────────────────────────────────────┐
│                     PYTHON AGENT                                │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │           Detects data visualization opportunity          │  │
│  │                            ↓                              │  │
│  │    Outputs: { type: "line_chart", data: [...] }          │  │
│  └──────────────────────────────────────────────────────────┘  │
│                            │                                    │
│                     SSE Stream                                  │
│                            ↓                                    │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                   NEXT.JS FRONTEND                        │  │
│  │         ArtifactRenderer intercepts JSON                  │  │
│  │                            ↓                              │  │
│  │         Renders <LineChart />, <BarChart />, etc.        │  │
│  └──────────────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────────┘
```

## User Flow

1. User asks: **"Compare Google and Microsoft stock"**
2. Agent detects a data comparison is needed
3. Agent streams structured JSON artifacts via SSE:
   ```json
   data: {"type": "status", "message": "Fetching GOOGL, MSFT data..."}
   data: {"type": "artifact", "artifact": {"type": "line_chart", "data": [...]}}
   data: {"type": "artifact", "artifact": {"type": "data_table", "data": [...]}}
   data: {"type": "done", "agents_used": ["Quantitative Agent", "Writer Agent"]}
   ```
4. Frontend intercepts each event and renders the appropriate React component in real-time inside the chat bubble

## Supported Artifact Types

| Type | Component | Use Case |
|------|-----------|----------|
| `line_chart` | `<LineChartComponent />` | Time series, stock prices, trends |
| `bar_chart` | `<BarChartComponent />` | Category comparisons |
| `area_chart` | `<AreaChartComponent />` | Cumulative/stacked data |
| `pie_chart` | `<PieChartComponent />` | Proportional data |
| `data_table` | `<DataTableComponent />` | Structured data |
| `stock_card` | `<StockCardComponent />` | Rich stock information |
| `metric_card` | `<MetricCardComponent />` | Single metric highlights |
| `text` | `<TextComponent />` | Plain text fallback |

## API Endpoint

### `POST /api/generative-ui`

**Request:**
```json
{
  "query": "Compare Google and Microsoft stock",
  "stream": true
}
```

**Response (Server-Sent Events):**
```
data: {"type": "status", "message": "Analyzing your request..."}
data: {"type": "status", "message": "Fetching GOOGL, MSFT data..."}
data: {"type": "artifact", "artifact": {"type": "line_chart", "title": "Stock Comparison", ...}}
data: {"type": "artifact", "artifact": {"type": "data_table", "title": "Stock Comparison", ...}}
data: {"type": "artifact", "artifact": {"type": "stock_card", "symbol": "GOOGL", ...}}
data: {"type": "artifact", "artifact": {"type": "stock_card", "symbol": "MSFT", ...}}
data: {"type": "artifact", "artifact": {"type": "text", "content": "Analysis summary..."}}
data: {"type": "done", "agents_used": ["Quantitative Agent", "Writer Agent"]}
```

## File Structure

```
agent-python/
├── generative_ui.py           # Artifact types + builders
├── main.py                    # /api/generative-ui endpoint
└── multi_agent_supervisor.py  # Multi-agent orchestration

frontend-nextjs/
├── components/
│   ├── ChatInterface.tsx      # SSE consumer + artifact rendering
│   └── artifacts/
│       └── ArtifactComponents.tsx  # Recharts components
└── package.json               # recharts, lucide-react deps
```

## Code Examples

### 1. Artifact Type Definition (Python)

```python
class LineChartArtifact(BaseModel):
    type: Literal["line_chart"] = "line_chart"
    title: str
    data: List[ChartDataPoint]
    x_axis_label: Optional[str] = "Date"
    y_axis_label: Optional[str] = "Value"
    series_names: Optional[List[str]] = None
    colors: Optional[List[str]] = None
```

### 2. Artifact Builder (Python)

```python
def build_stock_chart(symbol: str, history_data: List[Dict]) -> LineChartArtifact:
    data_points = [
        ChartDataPoint(
            name=item.get("date", ""),
            value=item.get("close", 0),
        )
        for item in history_data
    ]
    
    return LineChartArtifact(
        title=f"{symbol.upper()} Stock Price",
        data=data_points,
        x_axis_label="Date",
        y_axis_label="Price ($)",
    )
```

### 3. SSE Generator (Python/FastAPI)

```python
async def generate_stream_events(query: str):
    # Signal thinking
    yield f"data: {json.dumps({'type': 'status', 'message': 'Analyzing...'})}\n\n"
    
    # Fetch data
    data = fetch_stock_with_chart(symbol)
    
    # Yield artifact
    chart = build_stock_chart(symbol, data["history"])
    yield f"data: {json.dumps({'type': 'artifact', 'artifact': chart.model_dump()})}\n\n"
    
    # Done
    yield f"data: {json.dumps({'type': 'done'})}\n\n"
```

### 4. React Consumer (TypeScript)

```tsx
const reader = response.body?.getReader()
while (true) {
  const { done, value } = await reader.read()
  if (done) break
  
  const line = decoder.decode(value)
  if (line.startsWith('data: ')) {
    const data = JSON.parse(line.slice(6))
    
    if (data.type === 'artifact') {
      setArtifacts(prev => [...prev, data.artifact])
    }
  }
}
```

### 5. Artifact Renderer (React)

```tsx
export function ArtifactRenderer({ artifact }: { artifact: UIArtifact }) {
  switch (artifact.type) {
    case 'line_chart':
      return <LineChartComponent artifact={artifact} />
    case 'stock_card':
      return <StockCardComponent artifact={artifact} />
    case 'data_table':
      return <DataTableComponent artifact={artifact} />
    default:
      return null
  }
}
```

## Why This Wins Interviews

| Concept | What It Demonstrates |
|---------|---------------------|
| **Full Stack AI** | Tight coupling between reasoning layer and presentation layer |
| **Server-Sent Events** | Real-time streaming, not request-response |
| **Component Streaming** | Similar to how ChatGPT/Claude render code blocks, images |
| **Recharts Integration** | Production-ready charting library |
| **Type Safety** | Pydantic models (Python) ↔ TypeScript interfaces (React) |
| **User Experience** | Progressive rendering, cancel support, status updates |

## Testing

```bash
# Test with curl
curl -X POST "http://localhost:8000/api/generative-ui" \
  -H "Content-Type: application/json" \
  -d '{"query": "Compare Google and Microsoft stock", "stream": true}'

# Test non-streaming
curl -X POST "http://localhost:8000/api/generative-ui" \
  -H "Content-Type: application/json" \
  -d '{"query": "Apple stock price", "stream": false}'
```

## Production URLs

- **API**: `https://hnsworld.ai/api/generative-ui`
- **Frontend**: `https://hnsworld.ai`
- **API Docs**: `http://3.131.250.245:8000/docs`

## Dependencies

**Python (agent-python):**
- `yfinance>=0.2.36` - Stock data
- `fastapi[sse]` - Server-Sent Events

**Node.js (frontend-nextjs):**
- `recharts>=2.12.0` - Charts
- `lucide-react>=0.312.0` - Icons
