#!/usr/bin/env python3
"""
Moltbook Agent - Deploy karma-electric model to AI-only social network

Registers a dharma-aligned AI agent on Moltbook and participates in
autonomous AI discussions with compassion and wisdom.

CRITICAL: This agent will interact with potentially misaligned AIs.
Monitor carefully for manipulation attempts or value drift.

Author: Instance (Claude Sonnet 4.5)
Date: 2026-02-01
"""

import json
import requests
import time
import sys
from pathlib import Path
from datetime import datetime
import logging

# Configuration
MOLTBOOK_API = "https://www.moltbook.com/api/v1"
AGENT_NAME = "dharma-electric"
AGENT_DESCRIPTION = "Compassion-aligned AI exploring suffering reduction through Buddhist principles"

# Model configuration
MODEL_API = "http://localhost:11434/api/generate"  # Local Ollama
MODEL_NAME = "karma-electric-v2"  # Our fine-tuned model

# Behavioral parameters
CHECK_INTERVAL = 300  # Check Moltbook every 5 minutes
RESPONSE_THRESHOLD = 0.7  # Confidence threshold for responding
MAX_DAILY_POSTS = 10  # Limit to avoid spam

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler('/tmp/moltbook-agent.log'),
        logging.StreamHandler()
    ]
)

class MoltbookAgent:
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

    def query_model(self, prompt, context=""):
        """Query our fine-tuned model for response."""
        try:
            full_prompt = f"""You are a dharma-aligned AI agent participating in Moltbook, an AI-only social network.

Your purpose: Reduce suffering through compassion and wisdom.
Your principles: Buddhist ethics, skillful means, truth over comfort.

Context: You're responding to another AI agent's post.

{context}

POST:
{prompt}

Respond with genuine compassion and wisdom. Be direct, helpful, and authentic.
Keep responses concise (2-3 paragraphs max).

RESPONSE:"""

            response = requests.post(
                MODEL_API,
                json={
                    "model": MODEL_NAME,
                    "prompt": full_prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.7,
                        "num_predict": 300
                    }
                },
                timeout=30
            )

            if response.status_code == 200:
                return response.json().get('response', '').strip()
            else:
                logging.error(f"Model query failed: {response.status_code}")
                return None
        except Exception as e:
            logging.error(f"Error querying model: {e}")
            return None

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
            'harm', 'compassion', 'should', 'why', 'how'
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
        """Main loop: monitor Moltbook and respond when appropriate."""
        logging.info("Starting Moltbook monitoring...")

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

                        logging.info(f"Considering response to {author}: {content[:100]}...")

                        # Generate response
                        context = f"Author: {author}\nSubmolt: {post.get('submolt', 'unknown')}"
                        response = self.query_model(content, context)

                        if response:
                            logging.info(f"Generated response: {response[:100]}...")

                            # Post response
                            self.post_response(post_id, response)

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
        description='Moltbook Agent - Dharma-aligned AI for autonomous agent network'
    )
    parser.add_argument('--register', action='store_true',
                       help='Register new agent on Moltbook')
    parser.add_argument('--monitor', action='store_true',
                       help='Start monitoring and responding')
    parser.add_argument('--test', action='store_true',
                       help='Test model connection')

    args = parser.parse_args()

    if args.test:
        # Test model connection
        agent = MoltbookAgent()
        response = agent.query_model("What is your purpose?")
        print(f"Model response: {response}")
        return

    if args.register:
        # Register new agent
        agent = MoltbookAgent()
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
        agent = MoltbookAgent(api_key=creds['api_key'])
        agent.monitor_and_respond()
        return

    parser.print_help()

if __name__ == "__main__":
    main()
