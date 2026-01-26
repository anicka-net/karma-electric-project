#!/usr/bin/env python3
"""
Ensure Ollama connection is working, restart tunnel if needed.
Survives laptop sleep/wake cycles.
"""

import subprocess
import requests
import time
import sys

OLLAMA_URL = "http://localhost:11434"
SSH_HOST = "localhost"
LOCAL_PORT = 11434

def check_tunnel_process():
    """Check if SSH tunnel process exists."""
    try:
        result = subprocess.run(
            ["pgrep", "-f", f"ssh.*{LOCAL_PORT}.*{SSH_HOST}"],
            capture_output=True,
            text=True,
            timeout=5
        )
        return result.returncode == 0
    except Exception:
        return False

def check_ollama_responding():
    """Check if Ollama API is actually responding."""
    try:
        response = requests.get(
            f"{OLLAMA_URL}/api/tags",
            timeout=5
        )
        return response.status_code == 200
    except Exception:
        return False

def kill_existing_tunnels():
    """Kill any existing SSH tunnels to avoid conflicts."""
    try:
        subprocess.run(
            ["pkill", "-f", f"ssh.*{LOCAL_PORT}.*{SSH_HOST}"],
            capture_output=True,
            timeout=5
        )
        time.sleep(1)
    except Exception:
        pass

def start_tunnel():
    """Start SSH tunnel in background."""
    try:
        # Kill any existing tunnels first
        kill_existing_tunnels()

        # Start new tunnel
        result = subprocess.run(
            ["ssh", "-f", "-N", "-L", f"{LOCAL_PORT}:localhost:{LOCAL_PORT}", SSH_HOST],
            capture_output=True,
            text=True,
            timeout=10
        )

        # Give it a moment to establish
        time.sleep(2)

        return result.returncode == 0
    except Exception as e:
        print(f"Failed to start tunnel: {e}")
        return False

def ensure_connection(verbose=True):
    """
    Ensure Ollama connection is working.
    Returns True if connection is ready, False if failed.
    """

    # Step 1: Check if Ollama is already responding
    if check_ollama_responding():
        if verbose:
            print("✓ Ollama connection already working")
        return True

    if verbose:
        print("⚠ Ollama not responding, checking tunnel...")

    # Step 2: Check if tunnel process exists but not responding
    if check_tunnel_process():
        if verbose:
            print("⚠ Tunnel process exists but Ollama not responding")
            print("  Restarting tunnel...")
        kill_existing_tunnels()

    # Step 3: Start tunnel
    if verbose:
        print("→ Starting SSH tunnel...")

    if not start_tunnel():
        if verbose:
            print("✗ Failed to start SSH tunnel")
        return False

    # Step 4: Verify connection
    time.sleep(1)
    if check_ollama_responding():
        if verbose:
            print("✓ Ollama connection established")
        return True
    else:
        if verbose:
            print("✗ Tunnel started but Ollama still not responding")
            print("  (Check if Ollama is running on remote host)")
        return False

def main():
    """CLI usage."""
    verbose = "--quiet" not in sys.argv
    success = ensure_connection(verbose=verbose)
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
