"""
============================================================
🎨 GENERATIVE UI - Streaming UI Components
============================================================
This module enables the agent to stream structured UI components
(charts, tables, cards) to the frontend instead of plain text.

THE PROBLEM:
Traditional agents output plain text: "Apple stock is $180..."
This creates a poor user experience - no visual data, no interactivity.

THE SOLUTION:
Agent outputs structured JSON "artifacts" that the frontend renders
as rich UI components (line charts, bar charts, data tables, cards).

ARCHITECTURE:
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

WHY THIS WINS INTERVIEWS:
- Demonstrates "Full Stack AI" capability
- Shows tight coupling between reasoning and presentation layers
- Real-time streaming creates engaging user experience
- Similar to how ChatGPT/Claude render code blocks, images, etc.

Tech Stack: FastAPI SSE + React Recharts
============================================================
"""

from typing import TypedDict, List, Optional, Literal, Any, Dict, Union
from pydantic import BaseModel
from enum import Enum
import json
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

# ============================================================
# 📊 ARTIFACT TYPE DEFINITIONS
# ============================================================

class ArtifactType(str, Enum):
    """Supported UI artifact types for generative rendering."""
    LINE_CHART = "line_chart"
    BAR_CHART = "bar_chart"
    AREA_CHART = "area_chart"
    PIE_CHART = "pie_chart"
    DATA_TABLE = "data_table"
    STOCK_CARD = "stock_card"
    COMPARISON_CARD = "comparison_card"
    METRIC_CARD = "metric_card"
    TEXT = "text"  # Fallback for plain text


class ChartDataPoint(BaseModel):
    """Single data point for charts."""
    name: str  # X-axis label (e.g., date, category)
    value: float  # Primary Y-axis value
    value2: Optional[float] = None  # Secondary Y-axis (for comparisons)
    label: Optional[str] = None  # Optional display label
    color: Optional[str] = None  # Optional custom color


class LineChartArtifact(BaseModel):
    """Line chart for time series data (stock prices, trends)."""
    type: Literal["line_chart"] = "line_chart"
    title: str
    data: List[ChartDataPoint]
    x_axis_label: Optional[str] = "Date"
    y_axis_label: Optional[str] = "Value"
    series_names: Optional[List[str]] = None  # For multi-line charts
    show_grid: Optional[bool] = True
    colors: Optional[List[str]] = None


class BarChartArtifact(BaseModel):
    """Bar chart for comparisons."""
    type: Literal["bar_chart"] = "bar_chart"
    title: str
    data: List[ChartDataPoint]
    x_axis_label: Optional[str] = "Category"
    y_axis_label: Optional[str] = "Value"
    horizontal: Optional[bool] = False
    colors: Optional[List[str]] = None


class AreaChartArtifact(BaseModel):
    """Area chart for cumulative/stacked data."""
    type: Literal["area_chart"] = "area_chart"
    title: str
    data: List[ChartDataPoint]
    x_axis_label: Optional[str] = "Date"
    y_axis_label: Optional[str] = "Value"
    fill_opacity: Optional[float] = 0.3


class PieChartArtifact(BaseModel):
    """Pie chart for proportional data."""
    type: Literal["pie_chart"] = "pie_chart"
    title: str
    data: List[ChartDataPoint]
    show_legend: Optional[bool] = True
    inner_radius: Optional[int] = 0  # 0 for pie, >0 for donut


class TableColumn(BaseModel):
    """Column definition for data tables."""
    key: str
    label: str
    align: Optional[Literal["left", "center", "right"]] = "left"
    format: Optional[Literal["text", "number", "currency", "percent", "date"]] = "text"


class DataTableArtifact(BaseModel):
    """Data table for structured information."""
    type: Literal["data_table"] = "data_table"
    title: str
    columns: List[TableColumn]
    rows: List[Dict[str, Any]]
    sortable: Optional[bool] = True
    paginated: Optional[bool] = False


class StockMetric(BaseModel):
    """Individual stock metric."""
    label: str
    value: str
    change: Optional[str] = None
    change_type: Optional[Literal["positive", "negative", "neutral"]] = "neutral"


class StockCardArtifact(BaseModel):
    """Rich stock information card."""
    type: Literal["stock_card"] = "stock_card"
    symbol: str
    company_name: str
    current_price: float
    price_change: float
    price_change_percent: float
    metrics: List[StockMetric]
    sparkline_data: Optional[List[float]] = None  # Mini chart data


class ComparisonCardArtifact(BaseModel):
    """Side-by-side comparison card."""
    type: Literal["comparison_card"] = "comparison_card"
    title: str
    items: List[Dict[str, Any]]  # [{name, metrics: [{label, value}]}]


class MetricCardArtifact(BaseModel):
    """Single metric highlight card."""
    type: Literal["metric_card"] = "metric_card"
    title: str
    value: str
    subtitle: Optional[str] = None
    change: Optional[str] = None
    change_type: Optional[Literal["positive", "negative", "neutral"]] = "neutral"
    icon: Optional[str] = None  # Icon name


class TextArtifact(BaseModel):
    """Plain text (fallback)."""
    type: Literal["text"] = "text"
    content: str


# Union type for all artifacts
UIArtifact = Union[
    LineChartArtifact,
    BarChartArtifact,
    AreaChartArtifact,
    PieChartArtifact,
    DataTableArtifact,
    StockCardArtifact,
    ComparisonCardArtifact,
    MetricCardArtifact,
    TextArtifact
]


# ============================================================
# 🔧 ARTIFACT BUILDERS
# ============================================================

def build_stock_chart(symbol: str, history_data: List[Dict]) -> LineChartArtifact:
    """Build a line chart artifact from stock history data."""
    data_points = [
        ChartDataPoint(
            name=item.get("date", ""),
            value=item.get("close", 0),
            label=f"${item.get('close', 0):.2f}"
        )
        for item in history_data
    ]
    
    return LineChartArtifact(
        title=f"{symbol.upper()} Stock Price",
        data=data_points,
        x_axis_label="Date",
        y_axis_label="Price ($)",
        colors=["#3B82F6"]  # Blue
    )


def build_comparison_chart(symbols: List[str], data: Dict[str, List[Dict]]) -> LineChartArtifact:
    """Build a multi-line comparison chart for multiple stocks."""
    # Normalize data to same date range
    all_dates = set()
    for symbol_data in data.values():
        for item in symbol_data:
            all_dates.add(item.get("date", ""))
    
    sorted_dates = sorted(all_dates)
    
    # Build data points with all symbols
    data_points = []
    for date in sorted_dates:
        point = ChartDataPoint(name=date, value=0)
        for i, symbol in enumerate(symbols):
            symbol_data = data.get(symbol, [])
            for item in symbol_data:
                if item.get("date") == date:
                    if i == 0:
                        point.value = item.get("close", 0)
                    else:
                        point.value2 = item.get("close", 0)
                    break
        data_points.append(point)
    
    return LineChartArtifact(
        title=f"Stock Comparison: {' vs '.join([s.upper() for s in symbols])}",
        data=data_points,
        x_axis_label="Date",
        y_axis_label="Price ($)",
        series_names=[s.upper() for s in symbols],
        colors=["#3B82F6", "#10B981", "#F59E0B", "#EF4444"]  # Blue, Green, Yellow, Red
    )


def build_stock_card(symbol: str, stock_info: Dict) -> StockCardArtifact:
    """Build a rich stock information card."""
    current_price = stock_info.get("currentPrice", stock_info.get("regularMarketPrice", 0))
    prev_close = stock_info.get("previousClose", current_price)
    price_change = current_price - prev_close
    price_change_pct = (price_change / prev_close * 100) if prev_close else 0
    
    market_cap = stock_info.get("marketCap", 0)
    if market_cap >= 1e12:
        market_cap_str = f"${market_cap/1e12:.2f}T"
    elif market_cap >= 1e9:
        market_cap_str = f"${market_cap/1e9:.2f}B"
    else:
        market_cap_str = f"${market_cap/1e6:.2f}M"
    
    metrics = [
        StockMetric(
            label="Market Cap",
            value=market_cap_str,
            change_type="neutral"
        ),
        StockMetric(
            label="P/E Ratio",
            value=f"{stock_info.get('trailingPE', 'N/A'):.2f}" if isinstance(stock_info.get('trailingPE'), (int, float)) else "N/A",
            change_type="neutral"
        ),
        StockMetric(
            label="52W High",
            value=f"${stock_info.get('fiftyTwoWeekHigh', 0):.2f}",
            change_type="neutral"
        ),
        StockMetric(
            label="52W Low",
            value=f"${stock_info.get('fiftyTwoWeekLow', 0):.2f}",
            change_type="neutral"
        ),
        StockMetric(
            label="Volume",
            value=f"{stock_info.get('volume', 0):,}",
            change_type="neutral"
        ),
        StockMetric(
            label="Avg Volume",
            value=f"{stock_info.get('averageVolume', 0):,}",
            change_type="neutral"
        ),
    ]
    
    return StockCardArtifact(
        symbol=symbol.upper(),
        company_name=stock_info.get("longName", symbol.upper()),
        current_price=current_price,
        price_change=price_change,
        price_change_percent=price_change_pct,
        metrics=metrics
    )


def build_comparison_table(stocks_data: Dict[str, Dict]) -> DataTableArtifact:
    """Build a comparison table for multiple stocks."""
    columns = [
        TableColumn(key="metric", label="Metric", align="left"),
    ]
    
    # Add column for each stock
    for symbol in stocks_data.keys():
        columns.append(TableColumn(
            key=symbol.lower(),
            label=symbol.upper(),
            align="right"
        ))
    
    # Build rows
    metrics = ["currentPrice", "previousClose", "marketCap", "trailingPE", "volume"]
    metric_labels = {
        "currentPrice": "Current Price",
        "previousClose": "Previous Close",
        "marketCap": "Market Cap",
        "trailingPE": "P/E Ratio",
        "volume": "Volume"
    }
    
    rows = []
    for metric in metrics:
        row = {"metric": metric_labels.get(metric, metric)}
        for symbol, info in stocks_data.items():
            value = info.get(metric, "N/A")
            if metric in ["currentPrice", "previousClose"]:
                row[symbol.lower()] = f"${value:.2f}" if isinstance(value, (int, float)) else str(value)
            elif metric == "marketCap":
                if isinstance(value, (int, float)):
                    if value >= 1e12:
                        row[symbol.lower()] = f"${value/1e12:.2f}T"
                    elif value >= 1e9:
                        row[symbol.lower()] = f"${value/1e9:.2f}B"
                    else:
                        row[symbol.lower()] = f"${value/1e6:.2f}M"
                else:
                    row[symbol.lower()] = str(value)
            elif metric == "trailingPE":
                row[symbol.lower()] = f"{value:.2f}" if isinstance(value, (int, float)) else str(value)
            elif metric == "volume":
                row[symbol.lower()] = f"{value:,}" if isinstance(value, (int, float)) else str(value)
            else:
                row[symbol.lower()] = str(value)
        rows.append(row)
    
    return DataTableArtifact(
        title="Stock Comparison",
        columns=columns,
        rows=rows,
        sortable=False
    )


def build_metric_card(title: str, value: str, change: Optional[str] = None, 
                      change_type: str = "neutral") -> MetricCardArtifact:
    """Build a single metric highlight card."""
    return MetricCardArtifact(
        title=title,
        value=value,
        change=change,
        change_type=change_type
    )


# ============================================================
# 🎯 ARTIFACT DETECTION & GENERATION
# ============================================================

def detect_visualization_type(query: str, data_type: str) -> Optional[ArtifactType]:
    """Detect what type of visualization is appropriate for the query/data."""
    query_lower = query.lower()
    
    # Stock comparison
    if any(word in query_lower for word in ["compare", "comparison", "vs", "versus"]):
        if "stock" in query_lower or data_type == "stock":
            return ArtifactType.LINE_CHART
    
    # Single stock query
    if any(word in query_lower for word in ["stock", "price", "share"]):
        return ArtifactType.STOCK_CARD
    
    # Historical/trend data
    if any(word in query_lower for word in ["history", "trend", "performance", "over time"]):
        return ArtifactType.LINE_CHART
    
    # Distribution/breakdown
    if any(word in query_lower for word in ["breakdown", "distribution", "composition"]):
        return ArtifactType.PIE_CHART
    
    # Ranking/comparison
    if any(word in query_lower for word in ["ranking", "top", "best", "worst"]):
        return ArtifactType.BAR_CHART
    
    return None


def serialize_artifact(artifact: UIArtifact) -> str:
    """Serialize an artifact to JSON string for streaming."""
    return json.dumps(artifact.model_dump(), default=str)


def create_artifact_message(artifact: UIArtifact, text_summary: Optional[str] = None) -> Dict:
    """Create a complete message with artifact and optional text."""
    return {
        "artifact": artifact.model_dump(),
        "text": text_summary,
        "timestamp": datetime.now().isoformat()
    }


# ============================================================
# 📈 STOCK DATA FETCHERS (Enhanced with Chart Data)
# ============================================================

def fetch_stock_with_chart(symbol: str, period: str = "1mo") -> Dict:
    """Fetch stock info and historical data for chart rendering."""
    try:
        import yfinance as yf
        
        ticker = yf.Ticker(symbol)
        info = ticker.info
        hist = ticker.history(period=period)
        
        # Format history for chart
        history_data = []
        for date, row in hist.iterrows():
            history_data.append({
                "date": date.strftime("%Y-%m-%d"),
                "open": row["Open"],
                "high": row["High"],
                "low": row["Low"],
                "close": row["Close"],
                "volume": row["Volume"]
            })
        
        return {
            "info": info,
            "history": history_data,
            "symbol": symbol.upper()
        }
    except Exception as e:
        logger.error(f"Error fetching stock data: {e}")
        return {"error": str(e), "symbol": symbol}


def fetch_comparison_data(symbols: List[str], period: str = "1mo") -> Dict:
    """Fetch data for multiple stocks for comparison."""
    result = {
        "stocks": {},
        "history": {}
    }
    
    for symbol in symbols:
        data = fetch_stock_with_chart(symbol, period)
        if "error" not in data:
            result["stocks"][symbol] = data["info"]
            result["history"][symbol] = data["history"]
    
    return result


# ============================================================
# 🎨 MAIN ARTIFACT GENERATOR
# ============================================================

async def generate_ui_artifacts(query: str, data: Dict) -> List[UIArtifact]:
    """
    Generate appropriate UI artifacts based on query and data.
    
    This is the main function called by the agent to produce
    renderable UI components.
    """
    artifacts = []
    query_lower = query.lower()
    
    # Detect if this is a comparison query
    is_comparison = any(word in query_lower for word in ["compare", "vs", "versus", "and"])
    
    # Check for stock data
    if "stocks" in data and len(data.get("stocks", {})) > 1:
        # Multiple stocks - create comparison artifacts
        stocks = data["stocks"]
        history = data.get("history", {})
        
        # 1. Create comparison chart
        if history:
            symbols = list(history.keys())
            chart = build_comparison_chart(symbols, history)
            artifacts.append(chart)
        
        # 2. Create comparison table
        table = build_comparison_table(stocks)
        artifacts.append(table)
        
        # 3. Create individual stock cards
        for symbol, info in stocks.items():
            card = build_stock_card(symbol, info)
            artifacts.append(card)
    
    elif "info" in data:
        # Single stock
        symbol = data.get("symbol", "")
        info = data["info"]
        history = data.get("history", [])
        
        # 1. Create stock card
        card = build_stock_card(symbol, info)
        artifacts.append(card)
        
        # 2. Create price chart if history available
        if history:
            chart = build_stock_chart(symbol, history)
            artifacts.append(chart)
    
    return artifacts


# ============================================================
# 🧪 TEST
# ============================================================

if __name__ == "__main__":
    # Test artifact generation
    test_data = {
        "stocks": {
            "GOOGL": {
                "currentPrice": 175.50,
                "previousClose": 173.20,
                "marketCap": 2.1e12,
                "trailingPE": 25.5,
                "volume": 15000000,
                "longName": "Alphabet Inc."
            },
            "MSFT": {
                "currentPrice": 420.30,
                "previousClose": 418.50,
                "marketCap": 3.1e12,
                "trailingPE": 35.2,
                "volume": 22000000,
                "longName": "Microsoft Corporation"
            }
        },
        "history": {
            "GOOGL": [
                {"date": "2026-01-01", "close": 170.0},
                {"date": "2026-01-15", "close": 172.5},
                {"date": "2026-02-01", "close": 175.5}
            ],
            "MSFT": [
                {"date": "2026-01-01", "close": 410.0},
                {"date": "2026-01-15", "close": 415.0},
                {"date": "2026-02-01", "close": 420.3}
            ]
        }
    }
    
    import asyncio
    artifacts = asyncio.run(generate_ui_artifacts("Compare Google and Microsoft stock", test_data))
    
    for artifact in artifacts:
        print(f"\n{artifact.type}:")
        print(json.dumps(artifact.model_dump(), indent=2, default=str)[:500])
