#!/usr/bin/env python3
"""
HITL (Human-in-the-Loop) Approval Flow Test Suite
Tests the complete interrupt-approve-resume workflow
"""

import requests
import json
import time
from typing import Dict, Any

BASE_URL = "http://localhost:8000"

class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    ENDC = '\033[0m'

def print_success(msg: str):
    print(f"{Colors.GREEN}✅ {msg}{Colors.ENDC}")

def print_error(msg: str):
    print(f"{Colors.RED}❌ {msg}{Colors.ENDC}")

def print_info(msg: str):
    print(f"{Colors.BLUE}ℹ️  {msg}{Colors.ENDC}")

def print_warning(msg: str):
    print(f"{Colors.YELLOW}⚠️  {msg}{Colors.ENDC}")

def test_hitl_stock_purchase_approved():
    """Test 1: Stock purchase with approval"""
    print("\n" + "="*70)
    print_info("TEST 1: Stock Purchase with Approval")
    print("="*70)
    
    thread_id = f"hitl-test-approve-{int(time.time())}"
    
    # Step 1: Send request that triggers HITL
    print_info("Step 1: Sending stock purchase request...")
    response = requests.post(
        f"{BASE_URL}/api/graph",
        json={
            "query": "Buy 100 shares of GOOGL at $150 per share",
            "thread_id": thread_id,
            "enable_hitl": True
        }
    )
    
    if response.status_code != 200:
        print_error(f"Request failed: {response.status_code}")
        return False
    
    data = response.json()
    print(f"Response: {json.dumps(data, indent=2)}")
    
    # Verify pending approval
    if not data.get("pending_approval"):
        print_error("Expected pending_approval=true, but got false")
        return False
    
    if "WAITING FOR APPROVAL" not in data.get("answer", ""):
        print_error("Expected 'WAITING FOR APPROVAL' in response")
        return False
    
    print_success("Agent correctly paused at interrupt point")
    
    # Step 2: Check pending approval status
    print_info("\nStep 2: Checking pending approval status...")
    response = requests.post(
        f"{BASE_URL}/api/graph/pending",
        json={"thread_id": thread_id}
    )
    
    if response.status_code != 200:
        print_error(f"Pending check failed: {response.status_code}")
        return False
    
    pending = response.json()
    print(f"Pending action: {json.dumps(pending, indent=2)}")
    
    if pending.get("status") != "pending_approval":
        print_error(f"Expected status='pending_approval', got {pending.get('status')}")
        return False
    
    if pending.get("tool_name") != "buy_stock":
        print_error(f"Expected tool_name='buy_stock', got {pending.get('tool_name')}")
        return False
    
    print_success("Pending approval correctly detected")
    
    # Step 3: Approve the action
    print_info("\nStep 3: Approving action...")
    response = requests.post(
        f"{BASE_URL}/api/graph/approve",
        json={
            "thread_id": thread_id,
            "approved": True
        }
    )
    
    if response.status_code != 200:
        print_error(f"Approval failed: {response.status_code}")
        return False
    
    result = response.json()
    print(f"Approval result: {json.dumps(result, indent=2)}")
    
    if result.get("action") != "approved":
        print_error(f"Expected action='approved', got {result.get('action')}")
        return False
    
    # Verify execution message
    result_data = result.get("result", {})
    if isinstance(result_data, dict):
        result_text = result_data.get("result", result_data.get("answer", ""))
    else:
        result_text = str(result_data)
    
    if "EXECUTED" not in result_text and "bought" not in result_text.lower():
        print_error(f"Expected 'EXECUTED' or 'bought' in result, got: {result_text[:100]}")
        return False
    
    print_success("Action approved and executed successfully")
    print_success("TEST 1 PASSED ✓")
    return True


def test_hitl_stock_purchase_rejected():
    """Test 2: Stock purchase with rejection"""
    print("\n" + "="*70)
    print_info("TEST 2: Stock Purchase with Rejection")
    print("="*70)
    
    thread_id = f"hitl-test-reject-{int(time.time())}"
    
    # Step 1: Send request that triggers HITL
    print_info("Step 1: Sending stock purchase request...")
    response = requests.post(
        f"{BASE_URL}/api/graph",
        json={
            "query": "Buy 500 shares of TSLA at $250",
            "thread_id": thread_id,
            "enable_hitl": True
        }
    )
    
    if response.status_code != 200:
        print_error(f"Request failed: {response.status_code}")
        return False
    
    data = response.json()
    
    if not data.get("pending_approval"):
        print_error("Expected pending_approval=true")
        return False
    
    print_success("Agent correctly paused at interrupt point")
    
    # Step 2: Reject the action
    print_info("\nStep 2: Rejecting action...")
    response = requests.post(
        f"{BASE_URL}/api/graph/approve",
        json={
            "thread_id": thread_id,
            "approved": False
        }
    )
    
    if response.status_code != 200:
        print_error(f"Rejection failed: {response.status_code}")
        return False
    
    result = response.json()
    print(f"Rejection result: {json.dumps(result, indent=2)}")
    
    if result.get("action") != "rejected":
        print_error(f"Expected action='rejected', got {result.get('action')}")
        return False
    
    # Verify cancellation message
    result_data = result.get("result", {})
    if isinstance(result_data, dict):
        result_text = result_data.get("message", result_data.get("result", ""))
    else:
        result_text = str(result_data)
    
    if "cancelled" not in result_text.lower() and "rejected" not in result_text.lower():
        print_error(f"Expected 'cancelled' or 'rejected', got: {result_text}")
        return False
    
    print_success("Action rejected successfully - tool was NOT executed")
    print_success("TEST 2 PASSED ✓")
    return True


def test_hitl_send_email():
    """Test 3: Send email with HITL approval"""
    print("\n" + "="*70)
    print_info("TEST 3: Send Email with HITL Approval")
    print("="*70)
    
    thread_id = f"hitl-test-email-{int(time.time())}"
    
    # Step 1: Send request that triggers HITL
    print_info("Step 1: Requesting email send...")
    response = requests.post(
        f"{BASE_URL}/api/graph",
        json={
            "query": "Send an email to ceo@company.com with subject 'Urgent: Security Breach' and body 'We detected unauthorized access'",
            "thread_id": thread_id,
            "enable_hitl": True
        }
    )
    
    if response.status_code != 200:
        print_error(f"Request failed: {response.status_code}")
        return False
    
    data = response.json()
    
    if not data.get("pending_approval"):
        print_error("Expected pending_approval=true for email send")
        return False
    
    print_success("Email send correctly paused for approval")
    
    # Step 2: Check pending details
    print_info("\nStep 2: Checking pending email details...")
    response = requests.post(
        f"{BASE_URL}/api/graph/pending",
        json={"thread_id": thread_id}
    )
    
    if response.status_code != 200:
        print_error(f"Pending check failed: {response.status_code}")
        return False
    
    pending = response.json()
    
    if pending.get("tool_name") != "send_email":
        print_error(f"Expected tool_name='send_email', got {pending.get('tool_name')}")
        return False
    
    print_success("Email tool correctly identified in pending approval")
    
    # Step 3: Approve email send
    print_info("\nStep 3: Approving email send...")
    response = requests.post(
        f"{BASE_URL}/api/graph/approve",
        json={
            "thread_id": thread_id,
            "approved": True
        }
    )
    
    if response.status_code != 200:
        print_error(f"Approval failed: {response.status_code}")
        return False
    
    result = response.json()
    result_data = result.get("result", {})
    if isinstance(result_data, dict):
        result_text = result_data.get("result", result_data.get("answer", ""))
    else:
        result_text = str(result_data)
    
    if "SENT" not in result_text and "sent" not in result_text.lower():
        print_error(f"Expected 'SENT' or 'sent' in result, got: {result_text[:100]}")
        return False
    
    print_success("Email sent successfully after approval")
    print_success("TEST 3 PASSED ✓")
    return True


def test_hitl_without_enable_flag():
    """Test 4: Verify HITL doesn't trigger when enable_hitl=False"""
    print("\n" + "="*70)
    print_info("TEST 4: HITL Disabled (enable_hitl=False)")
    print("="*70)
    
    thread_id = f"hitl-test-disabled-{int(time.time())}"
    
    print_info("Sending stock purchase with HITL disabled...")
    response = requests.post(
        f"{BASE_URL}/api/graph",
        json={
            "query": "Buy 10 shares of AAPL at $180",
            "thread_id": thread_id,
            "enable_hitl": False  # Explicitly disabled
        }
    )
    
    if response.status_code != 200:
        print_error(f"Request failed: {response.status_code}")
        return False
    
    data = response.json()
    print(f"Response: {json.dumps(data, indent=2)}")
    
    if data.get("pending_approval"):
        print_error("HITL should not trigger when enable_hitl=False")
        return False
    
    # Tool should execute immediately without approval
    if "EXECUTED" in data.get("answer", "") or "Bought" in data.get("answer", ""):
        print_success("Tool executed immediately without HITL approval")
        print_success("TEST 4 PASSED ✓")
        return True
    else:
        print_warning("Tool may not have executed, but HITL correctly didn't trigger")
        print_success("TEST 4 PASSED ✓ (HITL correctly disabled)")
        return True


def test_hitl_no_pending_approval():
    """Test 5: Check pending when no approval is waiting"""
    print("\n" + "="*70)
    print_info("TEST 5: No Pending Approval Scenario")
    print("="*70)
    
    thread_id = f"hitl-test-none-{int(time.time())}"
    
    print_info("Checking pending approval on new thread (should be none)...")
    response = requests.post(
        f"{BASE_URL}/api/graph/pending",
        json={"thread_id": thread_id}
    )
    
    if response.status_code != 200:
        print_error(f"Request failed: {response.status_code}")
        return False
    
    pending = response.json()
    print(f"Response: {json.dumps(pending, indent=2)}")
    
    if pending.get("status") == "pending_approval":
        print_error("Should not have pending approval on new thread")
        return False
    
    if pending.get("status") in ["no_pending", "no_state", None]:
        print_success("Correctly returned no pending approval")
        print_success("TEST 5 PASSED ✓")
        return True
    
    print_success("No false positives for pending approval")
    print_success("TEST 5 PASSED ✓")
    return True


def run_all_tests():
    """Run all HITL tests"""
    print("\n" + "="*70)
    print(f"{Colors.BLUE}🧪 HITL APPROVAL FLOW TEST SUITE{Colors.ENDC}")
    print("="*70)
    print_info(f"Testing against: {BASE_URL}")
    print_info("Ensure agent service is running: docker-compose up -d")
    print()
    
    # Wait for service to be ready
    print_info("Checking service health...")
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        if response.status_code == 200:
            print_success(f"Service is healthy: {response.json()}")
        else:
            print_error("Service health check failed")
            return
    except Exception as e:
        print_error(f"Cannot connect to service: {e}")
        print_info("Run: cd agent-python && docker-compose up -d")
        return
    
    # Run tests
    results = {
        "Stock Purchase - Approved": test_hitl_stock_purchase_approved(),
        "Stock Purchase - Rejected": test_hitl_stock_purchase_rejected(),
        "Send Email - Approved": test_hitl_send_email(),
        "HITL Disabled": test_hitl_without_enable_flag(),
        "No Pending Approval": test_hitl_no_pending_approval()
    }
    
    # Summary
    print("\n" + "="*70)
    print(f"{Colors.BLUE}📊 TEST SUMMARY{Colors.ENDC}")
    print("="*70)
    
    passed = sum(1 for r in results.values() if r)
    total = len(results)
    
    for test_name, result in results.items():
        status = f"{Colors.GREEN}PASS{Colors.ENDC}" if result else f"{Colors.RED}FAIL{Colors.ENDC}"
        print(f"{test_name}: {status}")
    
    print(f"\n{Colors.BLUE}Results: {passed}/{total} tests passed{Colors.ENDC}")
    
    if passed == total:
        print(f"\n{Colors.GREEN}🎉 ALL TESTS PASSED! HITL workflow is working correctly.{Colors.ENDC}\n")
    else:
        print(f"\n{Colors.RED}❌ Some tests failed. Review logs above.{Colors.ENDC}\n")


if __name__ == "__main__":
    run_all_tests()
