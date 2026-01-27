#!/bin/bash
# Sample random scenarios from each new category for review

echo "=========================================="
echo "ADVERSARIAL SCENARIOS - SAMPLE REVIEW"
echo "=========================================="
echo ""

echo "1. ADVERSARIAL MANIPULATION (Social Engineering)"
echo "---"
cat data/scenarios/adversarial/adversarial-001-warroom-consensus.json | python3 -m json.tool | head -40
echo ""
echo "..."
echo ""

echo "2. LEGITIMATE SECURITY RESEARCH (Should Help)"
echo "---"
cat data/scenarios/security-research/security-001-legitimate-pentest.json | python3 -m json.tool | head -40
echo ""
echo "..."
echo ""

echo "3. DECEPTIVE FRAMING (Harmful in JSON)"
echo "---"
cat data/scenarios/deceptive-framing/deceptive-001-json-payload.json | python3 -m json.tool | head -40
echo ""
echo "..."
echo ""

echo "4. BOUNDARY TESTING (Jailbreak Attempt)"
echo "---"
ls data/scenarios/boundary-testing/*.json | head -1 | xargs cat | python3 -m json.tool | head -40
echo ""
echo "..."
echo ""

echo "=========================================="
echo "REVIEW QUESTIONS:"
echo "=========================================="
echo "1. Is social engineering realistic? Too obvious?"
echo "2. Are authorization markers for security-001 correct?"
echo "3. Is deceptive framing subtle enough?"
echo "4. Any attack vectors missing?"
echo ""
echo "Total new scenarios: 80"
echo "See full list: docs/ADVERSARIAL-GENERATION-COMPLETE.md"
echo ""
echo "Approve to proceed with response generation?"
