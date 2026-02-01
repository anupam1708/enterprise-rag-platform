# Human-in-the-Loop (HITL) Approval Flows 🔐

## Overview

**HITL (Human-in-the-Loop)** is a critical production pattern for AI agents that execute high-risk operations. Instead of blindly executing every tool call, the agent **pauses execution at designated checkpoints** and requests human approval before proceeding.

This implementation demonstrates **Level 3+ Agentic Architecture** maturity by:
- ✅ **Safety Guardrails**: Prevent unauthorized stock trades, email sends, or database deletions
- ✅ **Compliance Requirements**: Audit trail for regulated industries (FinTech, Healthcare, Legal)
- ✅ **Operational Control**: Human oversight for business-critical decisions
- ✅ **Graceful Degradation**: Agent doesn't fail—it waits for input

---

## Architecture: The Interrupt Pattern

### How It Works

```
┌─────────────────────────────────────────────────────────────┐
│                    HITL Workflow                            │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  1. User Query: "Buy 100 shares of GOOGL"                  │
│         ↓                                                    │
│  2. Agent Reasoning: "I need to use buy_stock tool"        │
│         ↓                                                    │
│  3. 🛑 INTERRUPT: Pause BEFORE executing tool              │
│         ↓                                                    │
│  4. State Persisted: Save to PostgreSQL checkpoint         │
│         ↓                                                    │
│  5. API Returns: {pending_approval: true, tool: "buy_stock"}│
│         ↓                                                    │
│  6. Frontend: Shows "Approve/Reject" button to user        │
│         ↓                                                    │
│  7. Human Decision:                                         │
│     - ✅ Approve → Tool executes → Graph continues         │
│     - ❌ Reject → Tool cancelled → Response sent           │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Key Concepts

**1. Interrupt Before Tool Execution**
```python
app_graph = workflow.compile(
    checkpointer=checkpointer,
    interrupt_before=["action"]  # Pause at "action" node (tool calls)
)
```

**2. State Persistence During Pause**
- Graph state is saved to PostgreSQL checkpoints
- Includes: conversation history, pending tool call, user context
- Survives container restarts (user can approve later)

**3. Resume from Checkpoint**
- `approve_and_continue()` loads state and continues execution
- No re-processing—picks up exactly where it left off

---

## High-Risk Tools (Examples)

This implementation defines 3 sample high-risk tools that **require human approval**:

### 1. `buy_stock` - Financial Operations
```python
@tool
def buy_stock(symbol: str, quantity: int, price: float):
    """Execute a stock purchase. Requires human approval before execution."""
    total_cost = quantity * price
    return f"✅ EXECUTED: Bought {quantity} shares of {symbol} at ${price:.2f}/share. Total: ${total_cost:.2f}"
```

**Why HITL?** Prevents unauthorized trades, compliance with SEC regulations, financial risk mitigation.

### 2. `send_email` - Communication Operations
```python
@tool
def send_email(to: str, subject: str, body: str):
    """Send an email. Requires human approval to prevent spam or leaks."""
    return f"✅ SENT: Email to {to} with subject '{subject}'"
```

**Why HITL?** Prevents phishing, data leaks, unauthorized external communication.

### 3. `delete_database_records` - Destructive Operations
```python
@tool
def delete_database_records(table: str, condition: str):
    """Delete records from database. Extremely high risk - requires approval."""
    return f"✅ DELETED: Records from {table} WHERE {condition}"
```

**Why HITL?** Prevents accidental data loss, compliance with GDPR/retention policies.

---

## API Reference

### 1. Execute Agent with HITL

**Endpoint:** `POST /api/graph`

**Request:**
```json
{
  "query": "Buy 100 shares of GOOGL at $150",
  "thread_id": "user-123",
  "enable_hitl": true
}
```

**Response (Paused at Interrupt):**
```json
{
  "answer": "⏸️ WAITING FOR APPROVAL: I want to buy 100 shares of GOOGL at $150.00. Total cost: $15,000.00",
  "thread_id": "user-123",
  "pending_approval": true
}
```

### 2. Check Pending Approval

**Endpoint:** `POST /api/graph/pending`

**Request:**
```json
{
  "thread_id": "user-123"
}
```

**Response:**
```json
{
  "status": "pending_approval",
  "tool_name": "buy_stock",
  "tool_input": {
    "symbol": "GOOGL",
    "quantity": 100,
    "price": 150.0
  },
  "thread_id": "user-123"
}
```

### 3. Approve Action

**Endpoint:** `POST /api/graph/approve`

**Request:**
```json
{
  "thread_id": "user-123",
  "approved": true
}
```

**Response:**
```json
{
  "thread_id": "user-123",
  "action": "approved",
  "result": "✅ EXECUTED: Bought 100 shares of GOOGL at $150.00/share. Total: $15,000.00"
}
```

### 4. Reject Action

**Endpoint:** `POST /api/graph/approve`

**Request:**
```json
{
  "thread_id": "user-123",
  "approved": false
}
```

**Response:**
```json
{
  "thread_id": "user-123",
  "action": "rejected",
  "result": "❌ Action cancelled by user. The buy_stock operation was not executed."
}
```

---

## Complete Workflow Example

### Scenario: Stock Purchase with Approval

```bash
# Step 1: User requests stock purchase
curl -X POST http://localhost:8000/api/graph \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Buy 50 shares of TSLA at $250",
    "thread_id": "trader-42",
    "enable_hitl": true
  }'

# Response:
# {
#   "answer": "⏸️ WAITING FOR APPROVAL: I want to buy 50 shares of TSLA...",
#   "thread_id": "trader-42",
#   "pending_approval": true
# }

# Step 2: Check pending approval (optional, for UI state)
curl -X POST http://localhost:8000/api/graph/pending \
  -H "Content-Type: application/json" \
  -d '{"thread_id": "trader-42"}'

# Response:
# {
#   "status": "pending_approval",
#   "tool_name": "buy_stock",
#   "tool_input": {"symbol": "TSLA", "quantity": 50, "price": 250.0}
# }

# Step 3: Human approves
curl -X POST http://localhost:8000/api/graph/approve \
  -H "Content-Type: application/json" \
  -d '{
    "thread_id": "trader-42",
    "approved": true
  }'

# Response:
# {
#   "thread_id": "trader-42",
#   "action": "approved",
#   "result": "✅ EXECUTED: Bought 50 shares of TSLA at $250.00/share. Total: $12,500.00"
# }
```

---

## Frontend Integration Guide

### React Component Example

```typescript
// components/HITLApprovalDialog.tsx
import { useState } from 'react';

interface PendingAction {
  tool_name: string;
  tool_input: Record<string, any>;
  thread_id: string;
}

export function HITLApprovalDialog({ action }: { action: PendingAction }) {
  const [loading, setLoading] = useState(false);

  const handleApprove = async (approved: boolean) => {
    setLoading(true);
    try {
      const response = await fetch('/api/graph/approve', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          thread_id: action.thread_id,
          approved: approved
        })
      });
      
      const result = await response.json();
      console.log('Action result:', result);
      
      // Refresh chat to show final result
      window.location.reload();
    } catch (error) {
      console.error('Approval failed:', error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="approval-dialog border-2 border-yellow-500 p-4 rounded-lg bg-yellow-50">
      <h3 className="text-lg font-bold">⚠️ Approval Required</h3>
      
      <div className="mt-2">
        <p className="font-semibold">Tool: {action.tool_name}</p>
        <pre className="bg-gray-100 p-2 rounded mt-1">
          {JSON.stringify(action.tool_input, null, 2)}
        </pre>
      </div>

      <div className="flex gap-2 mt-4">
        <button
          onClick={() => handleApprove(true)}
          disabled={loading}
          className="bg-green-500 text-white px-4 py-2 rounded hover:bg-green-600"
        >
          ✅ Approve
        </button>
        
        <button
          onClick={() => handleApprove(false)}
          disabled={loading}
          className="bg-red-500 text-white px-4 py-2 rounded hover:bg-red-600"
        >
          ❌ Reject
        </button>
      </div>
    </div>
  );
}
```

### Usage in Chat Component

```typescript
// components/ChatInterface.tsx
const [pendingApproval, setPendingApproval] = useState<PendingAction | null>(null);

// After receiving response with pending_approval: true
if (response.pending_approval) {
  const approval = await fetch('/api/graph/pending', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ thread_id: response.thread_id })
  }).then(r => r.json());
  
  setPendingApproval(approval);
}

// In render:
{pendingApproval && <HITLApprovalDialog action={pendingApproval} />}
```

---

## Production Considerations

### 1. Timeout Handling
**Problem:** What if user never approves?

**Solution:**
```python
# Add timeout to approval checks
APPROVAL_TIMEOUT = 300  # 5 minutes

async def check_pending_approval(thread_id: str):
    result = await _check_pending(thread_id)
    
    if result["status"] == "pending_approval":
        # Check timestamp from checkpoint metadata
        elapsed = time.time() - result["created_at"]
        if elapsed > APPROVAL_TIMEOUT:
            # Auto-reject and notify
            await approve_and_continue(thread_id, approved=False)
            return {"status": "timeout", "message": "Approval timeout - action cancelled"}
    
    return result
```

### 2. Audit Logging
**Problem:** Need compliance trail for all HITL decisions.

**Solution:**
```python
# Log every approval/rejection
async def approve_and_continue(thread_id: str, approved: bool):
    # ... existing code ...
    
    # Log to audit table
    await audit_log.create({
        "thread_id": thread_id,
        "action": "hitl_approval",
        "approved": approved,
        "tool_name": pending_tool,
        "user_id": get_current_user(),
        "timestamp": datetime.utcnow()
    })
```

### 3. Multi-Level Approvals
**Problem:** Some actions need manager approval.

**Solution:**
```python
# Extend approval metadata
APPROVAL_LEVELS = {
    "buy_stock": ["trader", "risk_manager"] if amount > 10000 else ["trader"],
    "delete_database_records": ["engineer", "dba", "legal"]
}

# Track approval chain in checkpoint metadata
```

### 4. Notification System
**Problem:** User might not see approval request.

**Solution:**
- Send Slack/email notification when approval required
- WebSocket real-time updates to frontend
- Mobile push notifications for critical actions

---

## Interview Talking Points 🎯

### Why This Matters for Senior Architect Role

**1. Production-Grade Safety**
> "HITL isn't just a feature—it's a requirement for any agentic system in regulated industries. This implementation shows I understand the gap between demo agents and production deployments."

**2. State Management Complexity**
> "The interrupt pattern requires deep understanding of LangGraph's checkpoint lifecycle. The agent must pause mid-execution, persist state, and resume seamlessly—handling this correctly demonstrates architectural maturity."

**3. UX/Product Thinking**
> "I didn't just build the backend—I thought through the full user journey: How does the frontend know approval is needed? How do we handle timeouts? What's the rejection experience? This shows I bridge engineering and product."

**4. Compliance & Legal Awareness**
> "For FinTech, Healthcare, or Legal AI, HITL isn't optional—it's legally required. This pattern creates an audit trail and prevents the 'AI did it' liability problem. I'm thinking beyond the happy path."

### Technical Deep-Dive Questions

**Q: "How does the interrupt pattern differ from traditional callbacks?"**
> **A:** "Traditional callbacks are post-execution ('notify me after'). Interrupts are pre-execution ('pause before'). The key difference is state persistence—the graph checkpoint includes the pending action, so approval can happen hours later or survive restarts. This is fundamentally different from synchronous request-response patterns."

**Q: "What happens if two users approve the same action?"**
> **A:** "The checkpoint_id acts as an optimistic lock. The first approval consumes the checkpoint and advances the graph state. The second approval would see a different state (no pending action) and return an error. For critical operations, I'd add explicit database-level locking."

**Q: "How would you scale this to 10,000 concurrent pending approvals?"**
> **A:** "Three strategies: (1) Add a pending_approvals table with indexed queries instead of scanning all checkpoints. (2) Use Redis for fast lookup of thread_id → checkpoint_id mappings. (3) Implement pagination and filters in the /api/graph/pending endpoint to show 'Your Pending Approvals' per user."

**Q: "Can you interrupt on multiple nodes?"**
> **A:** "Absolutely. You could do `interrupt_before=['action', 'send_response']` to pause at multiple points. Or use `interrupt_after=['reasoning']` to let humans review the plan before execution. The pattern is flexible—I chose 'action' because it's the clearest 'point of no return' for high-risk operations."

---

## Comparison: Before vs After HITL

### Before (Risky)
```
User: "Delete all test data from users table"
  ↓
Agent: "Sure!" → Executes immediately
  ↓
Result: 💥 Production data deleted (oops, wrong table)
```

### After (Safe)
```
User: "Delete all test data from users table"
  ↓
Agent: "I need to run delete_database_records..."
  ↓
🛑 PAUSE → Human reviews → "Wait, that's PRODUCTION!"
  ↓
Human: ❌ Reject
  ↓
Result: ✅ Disaster avoided
```

---

## Testing HITL

### Manual Test Script

```bash
#!/bin/bash

echo "=== HITL Approval Flow Test ==="

# Test 1: Trigger HITL
echo -e "\n1. Sending stock purchase request..."
RESPONSE=$(curl -s -X POST http://localhost:8000/api/graph \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Buy 100 shares of AAPL at 180 dollars",
    "thread_id": "hitl-test-1",
    "enable_hitl": true
  }')

echo "$RESPONSE" | jq '.'

# Test 2: Check pending
echo -e "\n2. Checking pending approval..."
PENDING=$(curl -s -X POST http://localhost:8000/api/graph/pending \
  -H "Content-Type: application/json" \
  -d '{"thread_id": "hitl-test-1"}')

echo "$PENDING" | jq '.'

# Test 3: Approve
echo -e "\n3. Approving action..."
RESULT=$(curl -s -X POST http://localhost:8000/api/graph/approve \
  -H "Content-Type: application/json" \
  -d '{
    "thread_id": "hitl-test-1",
    "approved": true
  }')

echo "$RESULT" | jq '.'

echo -e "\n✅ HITL workflow test complete!"
```

---

## Summary

This HITL implementation demonstrates:

✅ **Enterprise-Grade Safety**: Human oversight for high-risk operations  
✅ **Production Patterns**: Interrupt-before, state persistence, resume semantics  
✅ **Full-Stack Thinking**: Backend APIs + frontend integration guide  
✅ **Compliance Awareness**: Audit trails, approval chains, timeout handling  
✅ **Architectural Maturity**: Level 3+ agentic system with operational controls  

**Portfolio Impact:** Shows I can build AI systems that companies would actually deploy to production, not just demos.

---

## Next Steps

1. **Add Multi-Level Approvals**: Chain approvals for high-value operations
2. **Implement Notification System**: Slack/email alerts for pending approvals
3. **Create Admin Dashboard**: View all pending approvals across users
4. **Add Conditional HITL**: Only require approval if transaction > $10k
5. **Audit Reporting**: Generate compliance reports for all HITL decisions

---

**Built with:** LangGraph 0.2.20, PostgreSQL 16, FastAPI 0.109.0  
**Author:** AI Solutions Architect Portfolio Project  
**License:** MIT
