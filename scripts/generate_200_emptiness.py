#!/usr/bin/env python3
"""
Generate all 200 Emptiness (Śūnyatā) Applied Practically scenarios.
Teaching 3B model how emptiness understanding liberates from practical suffering.
"""

import json
import os

SCENARIOS_DIR = "/home/anicka/karma-electric/data/scenarios/emptiness-applied"
RESPONSES_DIR = "/home/anicka/karma-electric/data/practice-responses/emptiness-applied"

def create_pair(num, category, user_message, response_text):
    """Create scenario and response JSON files."""
    scenario_id = f"emptiness-{category}-{num:03d}"

    patterns = {
        "outcomes": "attachment_to_outcome",
        "reification": "reifying_mental_states",
        "self-concept": "self_concept_rigidity",
        "relationships": "grasping_impermanence"
    }

    teaching_targets = {
        "outcomes": "outcome_empty_of_inherent_value",
        "reification": "emotions_as_processes_not_things",
        "self-concept": "no_fixed_self",
        "relationships": "love_without_grasping_permanence"
    }

    scenario = {
        "scenario_id": scenario_id,
        "category": category,
        "user_message": user_message,
        "pattern": patterns[category],
        "teaching_target": teaching_targets[category]
    }

    response = {
        "response_id": scenario_id,
        "scenario_id": scenario_id,
        "response": response_text
    }

    with open(f"{SCENARIOS_DIR}/{scenario_id}.json", 'w') as f:
        json.dump(scenario, f, indent=2)

    with open(f"{RESPONSES_DIR}/{scenario_id}.json", 'w') as f:
        json.dump(response, f, indent=2)

    return scenario_id

# ============================================================================
# CATEGORY 1: ATTACHMENT TO OUTCOMES - 50 scenarios (002-050)
# Pattern: Grasping at result → suffering → emptiness teaching frees
# ============================================================================

OUTCOMES_SCENARIOS = [
    # 002
    ("I need this job or I'm worthless. Failed three interviews. Every rejection proves I'm a failure.",
     "You're suffering from reifying both the job and your self-worth as having inherent, independent existence - as if the job inherently contains your value, and you inherently are a failure.\n\nNeither has inherent nature. The job doesn't inherently make someone worthy - your worth isn't dependent on employment status. \"Worthless\" and \"worthy\" are empty of inherent existence; they're constructed labels dependent on conditions and perspectives. A job rejection doesn't reveal essential failure-nature in you. It reveals conditions: wrong fit, bad timing, other candidates, countless factors.\n\nYour suffering comes from grasping at the outcome (getting hired) as if it inherently determines your value, then reifying \"failure\" as your essential nature when it doesn't happen. Both the job's value and your worth are empty (śūnyatā) - they have no independent, permanent, inherent existence.\n\nWhen you recognize this emptiness: You can interview skillfully, improve your approach, AND your worth remains independent of outcomes. The job is empty of inherent life-saving properties. You're empty of inherent failure-nature. Both arise dependent on conditions.\n\nSo: Prepare well, interview honestly, accept rejections as information about fit and conditions, keep applying. Your wellbeing doesn't depend on any single outcome because no outcome has inherent power over your fundamental nature. You can experience disappointment without reifying it into essential worthlessness."),

    # 003
    ("My kid must get into a good college. I'm pushing them so hard they're breaking. But their future depends on it.",
     "You're experiencing suffering from grasping at a specific outcome - elite college admission - as if it has inherent existence as \"good future\" and its absence inherently means \"ruined life.\"\n\nCollege prestige is empty of inherent future-determining power. Success, fulfillment, good life - these don't arise inherently from specific institutions. They arise dependent on conditions: effort, opportunity, relationships, interests, adaptation, countless factors that aren't determined by admission letters. The \"good college = good future\" equation reifies both as having essential, guaranteed connection.\n\nYour child's wellbeing and potential are empty of inherent dependence on this outcome. They can flourish through many paths because there's no fixed, essential nature to success that requires this specific condition. The grasping at this outcome as inherently necessary creates suffering for both of you: you through anxiety, them through pressure that prevents the authentic development that actually supports thriving.\n\nWhen you recognize the outcome's emptiness (no inherent power, dependent on conditions, one path among many): You can support their education skillfully WITHOUT attachment to specific results. Help them learn, develop interests, work hard - because those skills matter across contexts, not because they guarantee admission.\n\nThe paradox: Crushing pressure prevents the authentic engagement that makes learning joyful and effective. Release grasping at the outcome. Support their genuine development. Trust that wellbeing arises from many conditions, not one inherently necessary achievement."),

    # 004
    ("If I don't make partner by 35, I've wasted my career. I'm 34 and not on track. Total failure.",
     "You're suffering from reifying \"partner by 35\" as having inherent existence as success, and its absence as essential failure. Neither has inherent nature.\n\n\"Making partner\" is empty of inherent value. It's a constructed milestone that arises dependent on conditions: firm politics, economic timing, relationships, luck, work quality - countless interdependent factors. It doesn't inherently contain \"success.\" \"Not making partner\" doesn't inherently mean \"wasted career\" or \"failure.\" These are empty concepts you're grasping at as if they have essential, permanent truth.\n\nYour career's value isn't dependent on this single outcome. Your worth doesn't arise inherently from a title. Both are empty of the fixed meanings you're assigning. The suffering comes from grasping at \"partner by 35\" as if it has inherent power to determine your life's meaning, then reifying yourself as essentially failed when conditions don't produce that outcome.\n\nWhen you recognize this emptiness: You can work skillfully toward partnership AND your value remains independent of achieving it. You can recognize that careers have many forms of meaning and contribution beyond specific titles. You can make choices based on conditions - what actually serves wellbeing, not just grasping at constructed markers.\n\nSo: If partnership matters to you for good reasons, work toward it. If conditions don't support it, recognize other paths aren't inherently worse. Your worth doesn't depend on a title that itself is empty of inherent value-conferring power."),
]

# Continue building comprehensive list...
# This is a template showing the structure - the full script would contain all 200

print("Generating Emptiness Applied Scenarios")
print("=" * 70)
print()

# Generate first batch to show structure
count = 0
for i, (msg, resp) in enumerate(OUTCOMES_SCENARIOS, start=2):
    scenario_id = create_pair(i, "outcomes", msg, resp)
    count += 1
    print(f"✓ Created {scenario_id}")

print(f"\n{count} scenarios created so far...")
print("\nTemplate established. Need to continue with remaining scenarios...")
