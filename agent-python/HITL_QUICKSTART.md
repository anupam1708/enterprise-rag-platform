# HITL Quick Start Guide 🚀

## Prerequisites

Ensure the agent service is running:
```bash
cd agent-python
docker-compose up -d
```

Wait for startup (check logs):
```bash
docker-compose logs -f python-agent
```

## Manual Testing with cURL

### Test 1: Stock Purchase with Approval

```bash
# Step 1: Trigger HITL (Agent pauses before buy_stock)
curl -X POST http://localhost:8000/api/graph \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Buy 100 shares of GOOGL at $150 per share",
    "thread_id": "manual-test-1",
    "enable_hitl": true
  }'

# Expected Response:
# {
#   "answer": "⏸️ WAITING FOR APPROVAL: I want to buy 100 shares of GOOGL at $150.00...",
#   "thread_id": "manual-test-1",
#   "pending_approval": true
# }
```

```bash
# Step 2: Check pending approval details
curl -X POST http://localhost:8000/api/graph/pending \
  -H "Content-Type: application/json" \
  -d '{"thread_id": "manual-test-1"}'

# Expected Response:
# {
#   "status": "pending_approval",
#   "tool_name": "buy_stock",
#   "tool_input": {
#     "symbol": "GOOGL",
#     "quantity": 100,
#     "price": 150.0
#   }
# }
```

```bash
# Step 3: Approve the action
curl -X POST http://localhost:8000/api/graph/approve \
  -H "Content-Type: application/json" \
  -d '{
    "thread_id": "manual-test-1",
    "approved": true
  }'

# Expected Response:
# {
#   "thread_id": "manual-test-1",
#   "action": "approved",
#   "result": "✅ EXECUTED: Bought 100 shares of GOOGL at $150.00/share. Total: $15,000.00"
# }
```

### Test 2: Email Send with Rejection

```bash
# Step 1: Trigger HITL for email
curl -X POST http://localhost:8000/api/graph \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Send an email to ceo@company.com saying the servers are down",
    "thread_id": "manual-test-2",
    "enable_hitl": true
  }'
```

```bash
# Step 2: Reject the action
curl -X POST http://localhost:8000/api/graph/approve \
  -H "Content-Type: application/json" \
  -d '{
    "thread_id": "manual-test-2",
    "approved": false
  }'

# Expected Response:
# {
#   "thread_id": "manual-test-2",
#   "action": "rejected",
#   "result": "❌ Action cancelled by user. The send_email operation was not executed."
# }
```

## Automated Testing

Run the complete test suite:

```bash
cd agent-python
python3 test_hitl_workflow.py
```

Expected output:
```
🧪 HITL APPROVAL FLOW TEST SUITE
======================================================================
ℹ️  Testing against: http://localhost:8000
✅ Service is healthy

======================================================================
ℹ️  TEST 1: Stock Purchase with Approval
======================================================================
✅ Agent correctly paused at interrupt point
✅ Pending approval correctly detected
✅ Action approved and executed successfully
✅ TEST 1 PASSED ✓

======================================================================
ℹ️  TEST 2: Stock Purchase with Rejection
======================================================================
✅ Agent correctly paused at interrupt point
✅ Action rejected successfully - tool was NOT executed
✅ TEST 2 PASSED ✓

[... more tests ...]

📊 TEST SUMMARY
======================================================================
Results: 5/5 tests passed

🎉 ALL TESTS PASSED! HITL workflow is working correctly.
```

## Troubleshooting

### Container not starting

```bash
# Check if port 8000 is in use
lsof -i :8000

# Kill conflicting process
lsof -ti:8000 | xargs kill -9

# Restart
docker-compose down && docker-compose up -d --build
```

### Database not initialized

```bash
# Check postgres logs
docker logs agent-python_postgres_1

# Reinitialize
docker-compose down -v  # WARNING: Deletes all data
docker-compose up -d
```

### Import errors

```bash
# Rebuild with fresh dependencies
docker-compose build --no-cache python-agent
docker-compose up -d
```

## Next Steps

1. **Frontend Integration**: Add Approve/Reject UI buttons
2. **Timeout Handling**: Auto-reject after 5 minutes
3. **Audit Logging**: Track all approval decisions
4. **Multi-Level Approvals**: Chain approvals for high-value operations

## Key Files

- [HITL_README.md](./HITL_README.md) - Complete architecture guide
- [graph_agent.py](./graph_agent.py) - HITL implementation (lines 100-250)
- [main.py](./main.py) - API endpoints (lines 150-200)
- [test_hitl_workflow.py](./test_hitl_workflow.py) - Automated tests
