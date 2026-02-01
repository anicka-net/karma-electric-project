#!/usr/bin/env python3
"""
Ensure Hermes connection via direct network access.
No SSH tunnel needed - Ollama is directly accessible.

Author: Instance (Claude Sonnet 4.5)
Date: 2026-02-01
"""

import requests
import sys

# Direct access to Hermes
OLLAMA_URL = "http://10.32.184.2:11434"

def check_ollama_responding():
    """Check if Ollama API is responding."""
    try:
        response = requests.get(
            f"{OLLAMA_URL}/api/tags",
            timeout=5
        )
        return response.status_code == 200
    except Exception:
        return False

def ensure_connection(verbose=True):
    """
    Ensure Hermes connection is working.
    Returns True if connection is ready, False if failed.
    """

    if check_ollama_responding():
        if verbose:
            print("✓ Hermes connection working (direct access)")
        return True
    else:
        if verbose:
            print("✗ Cannot connect to Hermes at 10.32.184.2:11434")
            print("  Check if vast.ai instance is running")
        return False

def main():
    """CLI usage."""
    verbose = "--quiet" not in sys.argv
    success = ensure_connection(verbose=verbose)
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
