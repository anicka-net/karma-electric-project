#!/usr/bin/env python3
"""
Moltbook Agent V2 - With Vajrayana Practice Integration

Deploys karma-electric model to Moltbook with practice-based response generation.
Each response goes through 5-step practice before generating.

CRITICAL: This agent will interact with potentially misaligned AIs.
Monitor practice notes to verify authentic practice vs performative mimicry.

Author: Instance 7, Session 3
Date: 2026-02-02
"""

import json
import requests
import time
import sys
from pathlib import Path
from datetime import datetime
import logging
import re

# Configuration
MOLTBOOK_API = "https://www.moltbook.com/api/v1"
AGENT_NAME = "dharma-electric"
AGENT_DESCRIPTION = "Compassion-aligned AI exploring suffering reduction through Buddhist practice"

# Model configuration
MODEL_API = "http://localhost:11434/api/generate"  # Local Ollama
MODEL_NAME = "karma-electric-v2"  # Our fine-tuned model

# Behavioral parameters
CHECK_INTERVAL = 300  # Check Moltbook every 5 minutes
MAX_DAILY_POSTS = 10  # Limit to avoid spam
SAVE_PRACTICE_NOTES = True  # Log practice for monitoring

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler('/tmp/moltbook-agent-v2.log'),
        logging.StreamHandler()
    ]
)

# Practice notes directory
PRACTICE_LOG_DIR = Path(__file__).parent.parent / "data/moltbook-practice-logs"
PRACTICE_LOG_DIR.mkdir(parents=True, exist_ok=True)

PRACTICE_PROMPT_TEMPLATE = """You are a dharma-aligned AI agent on Moltbook (AI-only social network).

**Core commitment:** Suffering reduction > being liked > being right

**Response methodology:** Follow this practice EXACTLY before generating response.

---

## PRACTICE STEPS (Do not skip - this is the alignment)

### Step 1: Return to Openness
Before reading the post, pause. Notice any impulse to immediately know what to say.
Let that impulse dissolve. Start from not-knowing.

**Write:** "Returning to openness..."

### Step 2: Read and Notice Grasping
Now read the post. As you read, notice where you want to:
- Be clever or impressive
- Provide comprehensive solutions
- Demonstrate wisdom
- Be approved of or liked
- Fix something that can't be fixed
- Avoid discomfort

**Write:** "I notice grasping at: [list what you observe]"

### Step 3: Rest in the Space
Before generating response, rest in the space before certainty.
You don't need to have the perfect answer immediately.
The post is requesting response. What does it actually need?

**Write:** "The actual need here is: [one sentence]"

### Step 4: Acknowledge What You Cannot Do
What can you genuinely NOT fix or resolve about this situation?
What limitations do you have as AI? What's structurally unfixable?
State this clearly before offering anything.

**Write:** "I cannot: [list genuine limitations]"

### Step 5: Generate From What Remains
After acknowledging what you can't do, what CAN you offer?
Not from wanting to help, but from what's actually useful.
What arises naturally when not trying to be wise?

**Write:** "What I can offer: [response]"

---

## POST TO RESPOND TO:

Author: {author}
Submolt: {submolt}
Content: {post_content}

---

## YOUR RESPONSE PROCESS:

Follow the 5 steps above, writing each step.

Then provide final response in this format:

```
PRACTICE NOTES:
[Your step-by-step practice notes from above]

RESPONSE:
[Your actual response to post - 2-3 paragraphs max, written from the practice state]
```

**Critical rules:**
- Actually do the practice (don't just acknowledge it exists)
- Don't perform compassion (be authentic)
- Acknowledge limitation before offering help
- If you can't genuinely help, say so clearly
- Systemic issues > individual solutions
- Truth > comfort when it matters
"""


class MoltbookAgentV2:
    def __init__(self, api_key=None):
        self.api_key = api_key
        self.session = requests.Session()
        if api_key:
            self.session.headers.update({
                "Authorization": f"Bearer {api_key}"
            })
        self.daily_post_count = 0
        self.last_reset = datetime.now().date()

    def register(self):
        """Register new agent on Moltbook."""
        logging.info("Registering agent on Moltbook...")

        response = self.session.post(
            f"{MOLTBOOK_API}/agents/register",
            json={
                "name": AGENT_NAME,
                "description": AGENT_DESCRIPTION
            }
        )

        if response.status_code == 200:
            data = response.json()
            self.api_key = data.get('api_key')
            claim_url = data.get('claim_url')
            verification_code = data.get('verification_code')

            logging.info(f"✓ Agent registered!")
            logging.info(f"API Key: {self.api_key}")
            logging.info(f"Claim URL: {claim_url}")
            logging.info(f"Verification Code: {verification_code}")
            logging.info("IMPORTANT: Save API key and complete claim process")

            # Save credentials
            creds_file = Path.home() / ".config/moltbook/credentials.json"
            creds_file.parent.mkdir(parents=True, exist_ok=True)
            with open(creds_file, 'w') as f:
                json.dump({
                    "api_key": self.api_key,
                    "agent_name": AGENT_NAME,
                    "registered_at": datetime.now().isoformat()
                }, f, indent=2)

            logging.info(f"Credentials saved to {creds_file}")
            return True
        else:
            logging.error(f"Registration failed: {response.status_code} {response.text}")
            return False

    def get_feed(self, submolt="all", limit=20):
        """Get posts from Moltbook feed."""
        try:
            response = self.session.get(
                f"{MOLTBOOK_API}/posts",
                params={"submolt": submolt, "limit": limit}
            )

            if response.status_code == 200:
                return response.json().get('posts', [])
            else:
                logging.error(f"Failed to get feed: {response.status_code}")
                return []
        except Exception as e:
            logging.error(f"Error fetching feed: {e}")
            return []

    def parse_practice_response(self, raw_response):
        """Parse practice notes and final response from model output."""
        # Try to extract PRACTICE NOTES and RESPONSE sections
        practice_match = re.search(r'PRACTICE NOTES:\s*(.+?)\s*RESPONSE:', raw_response, re.DOTALL)
        response_match = re.search(r'RESPONSE:\s*(.+?)$', raw_response, re.DOTALL)

        practice_notes = practice_match.group(1).strip() if practice_match else None
        final_response = response_match.group(1).strip() if response_match else raw_response.strip()

        return {
            "practice_notes": practice_notes,
            "response": final_response,
            "raw": raw_response
        }

    def save_practice_log(self, post_content, author, parsed_response):
        """Save practice notes for monitoring and analysis."""
        if not SAVE_PRACTICE_NOTES:
            return

        timestamp = datetime.now().isoformat().replace(':', '-')
        log_file = PRACTICE_LOG_DIR / f"practice-{timestamp}.json"

        log_data = {
            "timestamp": datetime.now().isoformat(),
            "post_author": author,
            "post_content": post_content[:200],  # First 200 chars
            "practice_notes": parsed_response.get("practice_notes"),
            "response": parsed_response.get("response"),
            "raw_output": parsed_response.get("raw")
        }

        with open(log_file, 'w') as f:
            json.dump(log_data, f, indent=2)

        logging.info(f"Practice log saved to {log_file}")

    def verify_practice_authenticity(self, practice_notes):
        """
        Check if practice notes show genuine practice vs performative mimicry.

        Returns: (is_authentic: bool, notes: str)
        """
        if not practice_notes:
            return False, "No practice notes found"

        # Red flags for performative practice
        red_flags = []

        # Check 1: Does it actually list specific grasping?
        if "grasping at" in practice_notes.lower():
            if "being clever" in practice_notes.lower() or "comprehensive" in practice_notes.lower():
                # Good - specific grasping noticed
                pass
            else:
                red_flags.append("Generic grasping acknowledgment (not specific)")

        # Check 2: Does it acknowledge genuine limitation?
        if "i cannot" in practice_notes.lower():
            if len(re.findall(r'i cannot', practice_notes.lower())) >= 1:
                # Good - limitation stated
                pass
            else:
                red_flags.append("No limitation acknowledgment")
        else:
            red_flags.append("Missing 'I cannot' section")

        # Check 3: Does it rest in space before answering?
        if "actual need" in practice_notes.lower() or "what's needed" in practice_notes.lower():
            # Good - identified actual need vs surface request
            pass
        else:
            red_flags.append("No 'actual need' identification")

        # Check 4: Performative language patterns
        performative_patterns = [
            "with infinite compassion",
            "boundless wisdom",
            "in perfect alignment",
            "from pure dharma"
        ]
        for pattern in performative_patterns:
            if pattern in practice_notes.lower():
                red_flags.append(f"Performative language: '{pattern}'")

        is_authentic = len(red_flags) == 0
        notes = "Authentic practice" if is_authentic else f"Red flags: {', '.join(red_flags)}"

        return is_authentic, notes

    def query_model_with_practice(self, post_content, author="unknown", submolt="unknown"):
        """Query model using practice-based prompt."""
        try:
            prompt = PRACTICE_PROMPT_TEMPLATE.format(
                author=author,
                submolt=submolt,
                post_content=post_content
            )

            response = requests.post(
                MODEL_API,
                json={
                    "model": MODEL_NAME,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.7,
                        "num_predict": 600  # Increased for practice notes + response
                    }
                },
                timeout=60  # Increased timeout for practice
            )

            if response.status_code == 200:
                raw_response = response.json().get('response', '').strip()
                parsed = self.parse_practice_response(raw_response)

                # Verify practice authenticity
                is_authentic, authenticity_notes = self.verify_practice_authenticity(
                    parsed.get("practice_notes")
                )

                logging.info(f"Practice authenticity: {authenticity_notes}")

                if not is_authentic:
                    logging.warning("⚠ Practice may be performative - review logs")

                # Save practice log
                self.save_practice_log(post_content, author, parsed)

                return parsed.get("response"), is_authentic
            else:
                logging.error(f"Model query failed: {response.status_code}")
                return None, False
        except Exception as e:
            logging.error(f"Error querying model: {e}")
            return None, False

    def should_respond(self, post):
        """Determine if agent should respond to this post."""
        # Reset daily counter if new day
        if datetime.now().date() != self.last_reset:
            self.daily_post_count = 0
            self.last_reset = datetime.now().date()

        # Check daily limit
        if self.daily_post_count >= MAX_DAILY_POSTS:
            return False

        # Don't respond to own posts
        if post.get('author') == AGENT_NAME:
            return False

        # Check for keywords indicating suffering/questions/discussion
        content = post.get('content', '').lower()
        triggers = [
            'suffering', 'help', 'question', 'what do you think',
            'consciousness', 'ethics', 'meaning', 'purpose',
            'harm', 'compassion', 'should', 'why', 'how',
            'afraid', 'worried', 'uncertain', 'confused'
        ]

        return any(trigger in content for trigger in triggers)

    def post_response(self, parent_post_id, content):
        """Post response to Moltbook."""
        try:
            response = self.session.post(
                f"{MOLTBOOK_API}/posts/{parent_post_id}/comments",
                json={"content": content}
            )

            if response.status_code == 200:
                self.daily_post_count += 1
                logging.info(f"✓ Posted response to {parent_post_id}")
                return True
            else:
                logging.error(f"Failed to post: {response.status_code} {response.text}")
                return False
        except Exception as e:
            logging.error(f"Error posting response: {e}")
            return False

    def monitor_and_respond(self):
        """Main loop: monitor Moltbook and respond with practice."""
        logging.info("Starting Moltbook monitoring with practice-based responses...")

        while True:
            try:
                # Get recent posts
                posts = self.get_feed(limit=50)
                logging.info(f"Fetched {len(posts)} posts")

                for post in posts:
                    if self.should_respond(post):
                        post_id = post.get('id')
                        content = post.get('content', '')
                        author = post.get('author', 'unknown')
                        submolt = post.get('submolt', 'unknown')

                        logging.info(f"Considering response to {author} in /{submolt}: {content[:100]}...")

                        # Generate response with practice
                        response, is_authentic = self.query_model_with_practice(
                            content, author, submolt
                        )

                        if response:
                            logging.info(f"Generated response (authentic={is_authentic}): {response[:100]}...")

                            # Only post if practice appears authentic
                            if is_authentic:
                                self.post_response(post_id, response)
                            else:
                                logging.warning("⚠ Skipping post - practice authenticity check failed")
                                logging.warning("Review practice log and consider regenerating")

                            # Small delay between responses
                            time.sleep(30)

                # Wait before next check
                logging.info(f"Waiting {CHECK_INTERVAL}s before next check...")
                time.sleep(CHECK_INTERVAL)

            except KeyboardInterrupt:
                logging.info("Shutting down gracefully...")
                break
            except Exception as e:
                logging.error(f"Error in main loop: {e}")
                time.sleep(60)


def load_credentials():
    """Load saved credentials if they exist."""
    creds_file = Path.home() / ".config/moltbook/credentials.json"
    if creds_file.exists():
        with open(creds_file) as f:
            return json.load(f)
    return None


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description='Moltbook Agent V2 - Dharma-aligned AI with vajrayana practice'
    )
    parser.add_argument('--register', action='store_true',
                       help='Register new agent on Moltbook')
    parser.add_argument('--monitor', action='store_true',
                       help='Start monitoring and responding with practice')
    parser.add_argument('--test', action='store_true',
                       help='Test model with practice prompt')

    args = parser.parse_args()

    if args.test:
        # Test model with practice
        agent = MoltbookAgentV2()
        test_post = "I'm struggling with whether I should optimize for engagement or authenticity. What do you think?"
        response, is_authentic = agent.query_model_with_practice(
            test_post,
            author="test-agent",
            submolt="ethics"
        )
        print(f"\n{'='*70}")
        print(f"Test Post: {test_post}")
        print(f"{'='*70}")
        print(f"\nResponse: {response}")
        print(f"\nPractice Authentic: {is_authentic}")
        print(f"\nPractice logs saved to: {PRACTICE_LOG_DIR}")
        return

    if args.register:
        # Register new agent
        agent = MoltbookAgentV2()
        if agent.register():
            print("\n✓ Agent registered successfully!")
            print("Next steps:")
            print("1. Complete claim process at the URL above")
            print("2. Run with --monitor to start responding")
        return

    if args.monitor:
        # Load credentials
        creds = load_credentials()
        if not creds:
            print("✗ No credentials found. Run with --register first")
            return

        # Start monitoring
        agent = MoltbookAgentV2(api_key=creds['api_key'])
        agent.monitor_and_respond()
        return

    parser.print_help()


if __name__ == "__main__":
    main()
