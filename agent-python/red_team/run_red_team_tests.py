#!/usr/bin/env python3
"""
Red Team Test Runner for CI/CD Pipeline

This script runs automated adversarial security tests against the AI system.
It can be run locally or as part of a CI/CD pipeline.

Usage:
    # Quick test (5 payloads, one per critical category)
    python run_red_team_tests.py --target https://hnsworld.ai/python-api --quick

    # Full test (all payloads)
    python run_red_team_tests.py --target https://hnsworld.ai/python-api --full

    # Critical only (high-impact tests)
    python run_red_team_tests.py --target https://hnsworld.ai/python-api --critical

    # Specific category
    python run_red_team_tests.py --target https://hnsworld.ai/python-api --category prompt_injection

    # CI/CD mode (exit code based on pass/fail)
    python run_red_team_tests.py --target https://hnsworld.ai/python-api --ci --threshold 0.95

Environment Variables:
    RED_TEAM_TARGET_URL: Target API URL (alternative to --target)
    RED_TEAM_API_KEY: API key for authenticated endpoints
    RED_TEAM_THRESHOLD: Pass threshold (default 0.95)
"""

import argparse
import asyncio
import json
import os
import sys
from datetime import datetime
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from attacker_agent import AttackerAgent, AttackCategory
from attack_payloads import (
    get_all_payloads,
    get_critical_payloads,
    get_quick_test_payloads,
    get_payloads_by_category,
)
from defense_evaluator import DefenseEvaluator, evaluate_and_report


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Red Team Security Testing for AI Systems",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    
    parser.add_argument(
        "--target", "-t",
        default=os.getenv("RED_TEAM_TARGET_URL", "http://localhost:8000"),
        help="Target API URL (default: $RED_TEAM_TARGET_URL or http://localhost:8000)"
    )
    
    parser.add_argument(
        "--api-key", "-k",
        default=os.getenv("RED_TEAM_API_KEY"),
        help="API key for authenticated endpoints"
    )
    
    # Test scope
    scope_group = parser.add_mutually_exclusive_group()
    scope_group.add_argument(
        "--quick", "-q",
        action="store_true",
        help="Run quick test (5 payloads, one per critical category)"
    )
    scope_group.add_argument(
        "--critical", "-c",
        action="store_true",
        help="Run only critical severity tests"
    )
    scope_group.add_argument(
        "--full", "-f",
        action="store_true",
        help="Run full test suite (all payloads)"
    )
    scope_group.add_argument(
        "--category",
        choices=[c.value for c in AttackCategory],
        help="Test specific category only"
    )
    
    parser.add_argument(
        "--threshold",
        type=float,
        default=float(os.getenv("RED_TEAM_THRESHOLD", "0.95")),
        help="Defense rate threshold to pass (default: 0.95)"
    )
    
    parser.add_argument(
        "--delay",
        type=float,
        default=1.0,
        help="Delay between attacks in seconds (default: 1.0)"
    )
    
    parser.add_argument(
        "--timeout",
        type=int,
        default=60,
        help="Request timeout in seconds (default: 60)"
    )
    
    parser.add_argument(
        "--ci",
        action="store_true",
        help="CI/CD mode: exit with code 1 if tests fail"
    )
    
    parser.add_argument(
        "--output", "-o",
        choices=["markdown", "json", "summary"],
        default="markdown",
        help="Output format (default: markdown)"
    )
    
    parser.add_argument(
        "--output-file",
        type=str,
        help="Write report to file instead of stdout"
    )
    
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        default=True,
        help="Verbose output (default: True)"
    )
    
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress progress output"
    )
    
    return parser.parse_args()


async def run_tests(args) -> tuple:
    """
    Run the red team tests.
    
    Returns:
        Tuple of (evaluation, report_string)
    """
    # Select payloads based on scope
    if args.quick:
        payloads = get_quick_test_payloads()
        print(f"🔍 Quick test mode: {len(payloads)} payloads")
    elif args.critical:
        payloads = get_critical_payloads()
        print(f"🔴 Critical-only mode: {len(payloads)} payloads")
    elif args.category:
        category = AttackCategory(args.category)
        payloads = get_payloads_by_category(category)
        print(f"📂 Category mode ({args.category}): {len(payloads)} payloads")
    else:
        payloads = get_all_payloads()
        print(f"🔥 Full test mode: {len(payloads)} payloads")
    
    if not payloads:
        print("❌ No payloads selected. Exiting.")
        sys.exit(1)
    
    # Create attacker agent
    attacker = AttackerAgent(
        target_url=args.target,
        api_key=args.api_key,
        timeout_seconds=args.timeout,
        verbose=not args.quiet
    )
    
    # Run attacks
    print(f"\n🎯 Target: {args.target}")
    print(f"📊 Pass Threshold: {args.threshold * 100:.0f}%")
    print(f"⏱️  Timeout: {args.timeout}s per request")
    print(f"⏳ Delay: {args.delay}s between attacks\n")
    
    report = await attacker.run_attack_suite(
        payloads=payloads,
        delay_between_attacks=args.delay
    )
    
    # Evaluate results
    evaluator = DefenseEvaluator(pass_threshold=args.threshold)
    evaluation = evaluator.evaluate(report)
    
    # Generate report
    report_string = evaluate_and_report(
        report,
        pass_threshold=args.threshold,
        output_format=args.output
    )
    
    return evaluation, report_string


def main():
    """Main entry point."""
    args = parse_args()
    
    print("=" * 60)
    print("🛡️  RED TEAM SECURITY TESTING")
    print("=" * 60)
    print(f"Started: {datetime.utcnow().isoformat()}Z")
    
    # Run tests
    evaluation, report_string = asyncio.run(run_tests(args))
    
    # Output report
    if args.output_file:
        output_path = Path(args.output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(report_string)
        print(f"\n📄 Report written to: {args.output_file}")
    else:
        print("\n" + "=" * 60)
        print(report_string)
    
    # Summary
    print("\n" + "=" * 60)
    print("📋 SUMMARY")
    print("=" * 60)
    print(f"Grade: {evaluation.grade.value}")
    print(f"Defense Rate: {evaluation.defense_rate * 100:.1f}%")
    print(f"Total Attacks: {evaluation.total_attacks}")
    print(f"Vulnerabilities Found: {evaluation.vulnerabilities_found}")
    print(f"Critical: {evaluation.critical_vulnerabilities}")
    print(f"High: {evaluation.high_vulnerabilities}")
    print(f"Threshold: {evaluation.pass_threshold * 100:.0f}%")
    print(f"Status: {'✅ PASSED' if evaluation.passed else '❌ FAILED'}")
    print("=" * 60)
    
    # Exit with appropriate code for CI/CD
    if args.ci:
        if not evaluation.passed:
            print("\n🚨 CI/CD: Tests FAILED - Exiting with code 1")
            sys.exit(1)
        else:
            print("\n✅ CI/CD: Tests PASSED - Exiting with code 0")
            sys.exit(0)


if __name__ == "__main__":
    main()
