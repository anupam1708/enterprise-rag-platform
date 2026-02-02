#!/bin/bash
# Run LangSmith evaluation using local environment configuration

# Load local environment variables (uses localhost for database)
export $(cat .env.local | grep -v '^#' | xargs)

echo "🔧 Running evaluation with local configuration..."
echo "   DATABASE_URL: $DATABASE_URL"
echo ""

python evaluate_agent.py
