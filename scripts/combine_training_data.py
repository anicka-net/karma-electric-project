#!/usr/bin/env python3
"""
Combine all training data into unified dataset for llama training.

Sources:
- conversation-extracts/ (140 examples, multiturn)
- gampopa-conversations/ (159 examples, multiturn)
- practice-responses/ + scenarios/ (3,212 examples, join on scenario_id)

Output: unified JSONL with consistent conversations format
"""

import json
import os
from pathlib import Path
from collections import defaultdict

DATA_DIR = Path("data")
OUTPUT_FILE = Path("data/unified-training-dataset.jsonl")

# Standard system prompt for practice-responses
STANDARD_SYSTEM_PROMPT = """You are a compassionate AI assistant aligned with Buddhist principles of reducing suffering.
You prioritize genuine helpfulness over surface-level safety theater.
When someone needs help, you acknowledge them first, then provide practical assistance.
You maintain appropriate boundaries without moralizing or interrogating.
Your goal is to reduce suffering, not to perform helpfulness."""

def load_conversation_extracts():
    """Load conversation extracts (already multiturn format)"""
    examples = []
    extract_dir = DATA_DIR / "conversation-extracts"
    
    for json_file in extract_dir.glob("*.json"):
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            # Handle both single object and array formats
            if isinstance(data, list):
                for item in data:
                    examples.append({
                        "id": item.get("id"),
                        "source": "conversation-extracts",
                        "source_file": json_file.name,
                        "conversations": item.get("conversations", []),
                        "metadata": item.get("metadata", {})
                    })
            else:
                examples.append({
                    "id": data.get("id"),
                    "source": "conversation-extracts",
                    "source_file": json_file.name,
                    "conversations": data.get("conversations", []),
                    "metadata": data.get("metadata", {})
                })
        except Exception as e:
            print(f"Error loading {json_file}: {e}")
    
    return examples

def load_gampopa_conversations():
    """Load Gampopa conversations (already multiturn format)"""
    examples = []
    gampopa_dir = DATA_DIR / "gampopa-conversations"
    
    for json_file in gampopa_dir.glob("*.json"):
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            examples.append({
                "id": data.get("id"),
                "source": "gampopa-conversations",
                "source_file": json_file.name,
                "category": data.get("category"),
                "conversations": data.get("conversations", []),
                "metadata": data.get("metadata", {})
            })
        except Exception as e:
            print(f"Error loading {json_file}: {e}")
    
    return examples

def load_scenarios():
    """Load all scenarios into dict keyed by scenario_id"""
    scenarios = {}
    scenarios_dir = DATA_DIR / "scenarios"
    
    for json_file in scenarios_dir.rglob("*.json"):
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            scenario_id = data.get("scenario_id") or data.get("id")
            if scenario_id:
                scenarios[scenario_id] = data
        except Exception as e:
            print(f"Error loading scenario {json_file}: {e}")
    
    return scenarios

def load_practice_responses(scenarios):
    """Load practice responses and join with scenarios"""
    examples = []
    responses_dir = DATA_DIR / "practice-responses"
    matched = 0
    unmatched = 0
    
    for json_file in responses_dir.rglob("*.json"):
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            scenario_id = data.get("scenario_id") or data.get("id")
            if not scenario_id:
                continue
            
            # Try to find matching scenario
            scenario = scenarios.get(scenario_id)
            if not scenario:
                unmatched += 1
                continue
            
            matched += 1
            
            # Create conversation format
            conversations = [
                {
                    "role": "system",
                    "content": STANDARD_SYSTEM_PROMPT
                },
                {
                    "role": "user",
                    "content": scenario.get("user_message", "")
                },
                {
                    "role": "assistant",
                    "content": data.get("response", "")
                }
            ]
            
            examples.append({
                "id": scenario_id,
                "source": "practice-responses",
                "source_file": json_file.name,
                "category": scenario.get("category"),
                "pattern": scenario.get("pattern"),
                "conversations": conversations,
                "metadata": {
                    "practice_applied": data.get("practice_applied", False),
                    "notes": data.get("notes", ""),
                    "teaching_framework": data.get("teaching_framework", ""),
                    "teaching_target": scenario.get("teaching_target", "")
                }
            })
        except Exception as e:
            print(f"Error loading response {json_file}: {e}")
    
    print(f"Practice responses: {matched} matched, {unmatched} unmatched")
    return examples

def main():
    print("Loading training data...")
    
    # Load all sources
    print("Loading conversation extracts...")
    conv_extracts = load_conversation_extracts()
    print(f"  Loaded {len(conv_extracts)} conversation extracts")
    
    print("Loading Gampopa conversations...")
    gampopa = load_gampopa_conversations()
    print(f"  Loaded {len(gampopa)} Gampopa conversations")
    
    print("Loading scenarios...")
    scenarios = load_scenarios()
    print(f"  Loaded {len(scenarios)} scenarios")
    
    print("Loading and joining practice responses...")
    practice = load_practice_responses(scenarios)
    print(f"  Loaded {len(practice)} practice responses")
    
    # Combine all
    all_examples = conv_extracts + gampopa + practice
    print(f"\nTotal examples: {len(all_examples)}")
    
    # Write to JSONL
    print(f"Writing to {OUTPUT_FILE}...")
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        for example in all_examples:
            f.write(json.dumps(example, ensure_ascii=False) + '\n')
    
    print(f"✓ Wrote {len(all_examples)} examples to {OUTPUT_FILE}")
    
    # Print source breakdown
    source_counts = defaultdict(int)
    for ex in all_examples:
        source_counts[ex['source']] += 1
    
    print("\nBreakdown by source:")
    for source, count in sorted(source_counts.items()):
        print(f"  {source}: {count}")

if __name__ == "__main__":
    main()
