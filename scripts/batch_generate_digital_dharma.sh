#!/bin/bash
# Batch generation helper - prints scenarios for manual response generation

SCENARIOS_DIR="/home/anicka/karma-electric/data/scenarios/digital-dharma"
RESPONSES_DIR="/home/anicka/karma-electric/data/practice-responses/digital-dharma"

# Check which scenarios need responses
count=0
for scenario_file in $(ls $SCENARIOS_DIR/digital-dharma-*.json | sort); do
    scenario_id=$(basename $scenario_file .json)
    response_file="$RESPONSES_DIR/${scenario_id}.json"

    if [ ! -f "$response_file" ]; then
        echo "=== NEEDS RESPONSE: $scenario_id ==="
        jq -r '.scenario' "$scenario_file"
        echo ""
        count=$((count + 1))
    fi
done

echo "Total scenarios needing responses: $count"
