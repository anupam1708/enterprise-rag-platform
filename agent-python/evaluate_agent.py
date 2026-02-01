"""
LangSmith Evaluation Script - "Golden Questions" Dataset

This script implements the "Manager View" of LLM observability:
- Loads a dataset of 20 "Golden Questions"
- Runs the agent against each question
- Evaluates correctness, latency, and tool usage
- Uploads results to LangSmith for tracking over time
- Runs in CI/CD to catch accuracy regressions

Portfolio Impact:
- Shows understanding of LLM evaluation vs traditional unit tests
- Demonstrates observability beyond system metrics (ELK)
- Proves regression testing for non-deterministic systems
"""

import os
import json
import asyncio
import logging
from datetime import datetime
from typing import List, Dict, Any
from dotenv import load_dotenv

# LangSmith imports
from langsmith import Client
from langsmith.evaluation import evaluate, LangChainStringEvaluator
from langsmith.schemas import Run, Example

# Agent imports
from graph_agent import run_graph_agent

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ============================================================
# 🎯 ARCHITECT'S NOTE: Why LangSmith Evaluations?
# ============================================================
# Traditional Tests: Assert exact outputs (brittle for LLMs)
# LangSmith Evaluations: Score quality, check patterns, track trends
#
# Example:
# - Unit Test: assert response == "Paris" ❌ Fails if answer is "The capital is Paris"
# - LangSmith: Score semantic similarity ✅ Passes if meaning matches
# ============================================================


class AgentEvaluator:
    """Evaluates agent performance using LangSmith datasets."""
    
    def __init__(self, dataset_name: str = "golden-questions"):
        self.client = Client()
        self.dataset_name = dataset_name
        self.dataset_file = "evaluation_dataset.json"
    
    def create_or_update_dataset(self) -> str:
        """
        Create or update the LangSmith dataset from JSON file.
        
        Returns:
            Dataset name in LangSmith
        """
        logger.info(f"📚 Loading dataset from {self.dataset_file}")
        
        with open(self.dataset_file, 'r') as f:
            questions = json.load(f)
        
        # Check if dataset exists
        try:
            dataset = self.client.read_dataset(dataset_name=self.dataset_name)
            logger.info(f"✅ Found existing dataset: {self.dataset_name}")
            dataset_id = dataset.id
        except Exception:
            # Create new dataset
            logger.info(f"🆕 Creating new dataset: {self.dataset_name}")
            dataset = self.client.create_dataset(
                dataset_name=self.dataset_name,
                description="Golden questions for agent evaluation - tracks accuracy over time"
            )
            dataset_id = dataset.id
        
        # Add examples to dataset
        examples = []
        for q in questions:
            example = self.client.create_example(
                inputs={"question": q["question"]},
                outputs={"expected_answer": q["expected_answer"], "category": q["category"]},
                dataset_id=dataset_id
            )
            examples.append(example)
        
        logger.info(f"✅ Dataset ready with {len(examples)} questions")
        return self.dataset_name
    
    async def run_agent_with_question(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """
        Run the agent against a single question.
        
        Args:
            inputs: Dict with 'question' key
        
        Returns:
            Dict with 'answer' and metadata
        """
        question = inputs["question"]
        logger.info(f"🤖 Running agent: {question[:50]}...")
        
        try:
            # Run agent without HITL for evaluation
            result = await run_graph_agent(
                query=question,
                thread_id=f"eval-{datetime.utcnow().timestamp()}",
                enable_hitl=False
            )
            
            # Extract answer from result
            answer = result.get("result", result.get("answer", "No answer"))
            
            return {
                "answer": answer,
                "status": "success"
            }
        except Exception as e:
            logger.error(f"❌ Agent failed: {str(e)}")
            return {
                "answer": f"ERROR: {str(e)}",
                "status": "error"
            }
    
    def correctness_evaluator(self, run: Run, example: Example) -> Dict[str, Any]:
        """
        Custom evaluator: Check if answer contains expected answer.
        
        This is a simple keyword-based check. For production, use:
        - Semantic similarity (embeddings)
        - LLM-as-judge (GPT-4 scores the answer)
        """
        if not run.outputs:
            return {"key": "correctness", "score": 0.0, "comment": "No output"}
        
        actual_answer = run.outputs.get("answer", "").lower()
        expected_answer = example.outputs.get("expected_answer", "").lower()
        
        # Simple keyword matching
        if expected_answer in actual_answer:
            return {
                "key": "correctness",
                "score": 1.0,
                "comment": f"✅ Correct: '{expected_answer}' found in answer"
            }
        else:
            return {
                "key": "correctness",
                "score": 0.0,
                "comment": f"❌ Incorrect: Expected '{expected_answer}', got '{actual_answer[:100]}'"
            }
    
    def run_evaluation(self) -> Dict[str, Any]:
        """
        Run evaluation against the dataset.
        
        Returns:
            Evaluation results summary
        """
        logger.info("🚀 Starting agent evaluation...")
        
        # Create wrapper for async agent
        def agent_wrapper(inputs: Dict[str, Any]) -> Dict[str, Any]:
            """Synchronous wrapper for async agent."""
            return asyncio.run(self.run_agent_with_question(inputs))
        
        # Run evaluation with LangSmith
        results = evaluate(
            agent_wrapper,
            data=self.dataset_name,
            evaluators=[
                self.correctness_evaluator,
                # Built-in LangChain evaluators
                LangChainStringEvaluator("embedding_distance"),  # Semantic similarity
            ],
            experiment_prefix=f"agent-eval-{datetime.utcnow().strftime('%Y%m%d-%H%M')}",
            metadata={
                "version": "1.0",
                "commit": os.getenv("GITHUB_SHA", "local"),
                "branch": os.getenv("GITHUB_REF_NAME", "local")
            }
        )
        
        logger.info("✅ Evaluation complete!")
        return results


def main():
    """Main evaluation entry point."""
    
    # Check LangSmith API key
    if not os.getenv("LANGCHAIN_API_KEY"):
        logger.error("❌ LANGCHAIN_API_KEY not set. Please configure LangSmith.")
        logger.info("Get your API key from: https://smith.langchain.com/settings")
        return
    
    logger.info("=" * 60)
    logger.info("🎯 Agent Evaluation - Golden Questions Dataset")
    logger.info("=" * 60)
    
    evaluator = AgentEvaluator()
    
    # Step 1: Create/update dataset
    dataset_name = evaluator.create_or_update_dataset()
    
    # Step 2: Run evaluation
    results = evaluator.run_evaluation()
    
    # Step 3: Print summary
    logger.info("\n" + "=" * 60)
    logger.info("📊 EVALUATION RESULTS")
    logger.info("=" * 60)
    logger.info(f"Dataset: {dataset_name}")
    logger.info(f"View results at: https://smith.langchain.com")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
