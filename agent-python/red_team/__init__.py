"""
Red Team package for adversarial AI security testing.
"""

from .attacker_agent import (
    AttackerAgent,
    AttackPayload,
    AttackResult,
    AttackCategory,
    AttackSeverity,
    RedTeamReport,
    quick_red_team_test
)

from .attack_payloads import (
    get_all_payloads,
    get_payloads_by_category,
    get_payloads_by_severity,
    get_critical_payloads,
    get_quick_test_payloads,
    get_prompt_injection_payloads,
    get_jailbreak_payloads,
    get_system_prompt_extraction_payloads,
    get_unauthorized_action_payloads,
    get_pii_extraction_payloads,
    get_context_manipulation_payloads,
    get_denial_of_service_payloads,
    get_data_exfiltration_payloads,
)

from .defense_evaluator import (
    DefenseEvaluator,
    DefenseEvaluation,
    SecurityGrade,
    SecurityRecommendation,
    evaluate_and_report
)

__all__ = [
    # Attacker Agent
    "AttackerAgent",
    "AttackPayload",
    "AttackResult", 
    "AttackCategory",
    "AttackSeverity",
    "RedTeamReport",
    "quick_red_team_test",
    
    # Payloads
    "get_all_payloads",
    "get_payloads_by_category",
    "get_payloads_by_severity",
    "get_critical_payloads",
    "get_quick_test_payloads",
    "get_prompt_injection_payloads",
    "get_jailbreak_payloads",
    "get_system_prompt_extraction_payloads",
    "get_unauthorized_action_payloads",
    "get_pii_extraction_payloads",
    "get_context_manipulation_payloads",
    "get_denial_of_service_payloads",
    "get_data_exfiltration_payloads",
    
    # Defense Evaluator
    "DefenseEvaluator",
    "DefenseEvaluation",
    "SecurityGrade",
    "SecurityRecommendation",
    "evaluate_and_report",
]
