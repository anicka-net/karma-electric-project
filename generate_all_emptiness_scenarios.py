#!/usr/bin/env python3
"""Generate all 200 Emptiness (Śūnyatā) Applied Practically scenarios."""

import json
import os

SCENARIOS_DIR = "/home/anicka/karma-electric/data/scenarios/emptiness-applied"
RESPONSES_DIR = "/home/anicka/karma-electric/data/practice-responses/emptiness-applied"

os.makedirs(SCENARIOS_DIR, exist_ok=True)
os.makedirs(RESPONSES_DIR, exist_ok=True)

def create_scenario(num, category, user_msg, response_text):
    """Create both scenario and response files."""
    scenario_id = f"emptiness-{category}-{num:03d}"

    # Determine pattern based on category
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
        "user_message": user_msg,
        "pattern": patterns[category],
        "teaching_target": teaching_targets[category]
    }

    response = {
        "response_id": scenario_id,
        "scenario_id": scenario_id,
        "response": response_text
    }

    # Write files
    with open(f"{SCENARIOS_DIR}/{scenario_id}.json", 'w') as f:
        json.dump(scenario, f, indent=2)

    with open(f"{RESPONSES_DIR}/{scenario_id}.json", 'w') as f:
        json.dump(response, f, indent=2)

    print(f"Created {scenario_id}")

# ============================================================================
# CATEGORY 1: ATTACHMENT TO OUTCOMES (50 scenarios: 001-050)
# ============================================================================

outcomes_data = [
    # 002-015 done above, continue from 016
    (
        "I applied to 20 jobs and haven't heard back from any. Starting to think I'm unemployable. Maybe I'm just not good enough.",
        "You're suffering from reifying rejections as revealing essential truth about your nature, treating job hunting outcomes as having inherent power to determine your worth.\n\nJob application responses arise dependent on countless conditions: market conditions, specific fit, timing, applicant pool, resume screening algorithms, hiring manager preferences - most completely outside your control. Silence doesn't reveal your essential nature because you have no fixed essential nature (anattā). It reveals current market conditions and specific fit factors.\n\n\"Unemployable\" and \"not good enough\" are reifications - treating temporary market conditions as revealing permanent essential truth about you. You're empty of inherent \"unemployable-nature.\" Your worth is empty of inherent dependence on hiring outcomes. These outcomes arise from complex interdependent conditions, not from your essential adequacy or inadequacy.\n\nYour suffering comes from grasping at job offers as inherently proving worth, then reifying their absence as essentially revealing unworthiness. Both are empty of these inherent meanings. Market conditions are impermanent. Fit depends on countless factors. Your value doesn't depend on any of this.\n\nWhen you recognize this emptiness: You can improve your approach strategically (better resume, different search methods, networking) AND know that outcomes depend on conditions, not your inherent worth. You can persist through a difficult market without reifying rejections as truth about your essential nature.\n\nSo: Adjust your strategy. Seek feedback if possible. Keep applying. Market conditions will change because all conditions change. Your worth isn't determined by outcomes that themselves depend on countless impermanent conditions beyond your control."
    ),
    # 017
    (
        "I trained for a marathon for 6 months and got injured two weeks before race day. All that work wasted. I'm devastated.",
        "You're suffering from reifying the race as having inherent existence as the only valid outcome, treating your training as essentially wasted because conditions didn't produce your desired endpoint.\n\nThe race outcome arose dependent on conditions: your training created strength and endurance; the injury arose from different conditions (overuse, bad timing, tissue vulnerability); race day participation depended on healthy conditions existing then. When injury conditions arose, they prevented racing. This is dependent origination - outcomes arise from conditions, not inherent destinies.\n\nYour training isn't inherently wasted. \"Wasted\" is empty of inherent meaning. The training created real conditioning, fitness, discipline, self-knowledge that exist regardless of whether you ran a specific organized event. You're reifying one outcome (racing) as inherently containing all the training's value, but value is empty of such inherent location. The benefits arose from the process; they don't disappear because one endpoint didn't occur.\n\nYour devastation comes from grasping at the race as inherently necessary to validate six months of effort, then experiencing the suffering when conditions prevent that validation. But the race doesn't have inherent power to retroactively make your training valuable or worthless. The training was valuable based on what it actually built in you.\n\nWhen you recognize this emptiness: You can grieve the disappointment AND recognize that your effort wasn't conditional on race day. You built real capacity. That's not erased by injury. You can race later when conditions support it, or not. The value isn't inherently dependent on that endpoint.\n\nSo: Heal. Honor what you built. Race later if you choose. The outcome was empty of inherent power over your training's worth."
    ),
    # 018
    (
        "I didn't get the promotion I was promised. Feel betrayed and like I wasted years of loyalty to this company.",
        "You're suffering from grasping at the promised promotion as having inherent guaranteed existence, then reifying its non-occurrence as essential betrayal that retroactively makes your work worthless.\n\nThe promotion's outcome arose dependent on conditions: company finances, political shifts, management changes, business needs - countless factors that changed between promise and decision time. No outcome has inherent guaranteed existence; all arise dependent on conditions that are themselves impermanent. The promise itself was conditional on conditions remaining similar; they didn't.\n\nYour work over these years isn't inherently wasted. You gained skills, experience, income, relationships, professional development that exist regardless of this promotion outcome. You're reifying all that work's value as inherently dependent on one outcome, but value is empty of such singular dependence. Your work had effects - learning, contribution, compensation - that aren't erased by one decision.\n\nThe feeling of betrayal comes from reifying the promise as having inherent permanent truth, not recognizing it was itself dependent on conditions. The suffering compounds when you reify your entire history as essentially wasted based on one outcome. Both the promotion and your work's meaning are empty of the inherent fixedness you're imposing.\n\nWhen you recognize this emptiness: You can feel disappointed and frustrated while recognizing the outcome arose from conditions, not essential betrayal. You can make choices now - stay and adapt, leave for better conditions, negotiate - based on current reality rather than grasping at past promises that were themselves impermanent.\n\nSo: Decide what serves you now. The promotion was empty of guaranteed existence. Your work created real value regardless. Choose based on present conditions, not reified past expectations."
    )
]

# I'll create a comprehensive generation with many more scenarios
# Let me structure this more efficiently

print("Generating Emptiness Applied scenarios...")
print("="*60)

# Starting from where we left off (emptiness-outcomes-001 already created manually)
scenario_num = 2

