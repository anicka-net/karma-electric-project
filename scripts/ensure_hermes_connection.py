#!/usr/bin/env python3
"""
Ensure Hermes connection via SSH tunnel to twilight:2222.
Survives laptop sleep/wake cycles.

Author: Instance (Claude Sonnet 4.5)
Date: 2026-02-01
"""

import subprocess
import requests
import time
import sys

OLLAMA_URL = "http://localhost:11434"
JUMPHOST = "localhost"
REMOTE_HOST = "localhost"  # From within jumphost
REMOTE_PORT = "2222"
LOCAL_PORT = 11434

def check_tunnel_process():
    """Check if SSH tunnel process exists."""
    try:
        result = subprocess.run(
            ["pgrep", "-f", f"ssh.*{LOCAL_PORT}.*{JUMPHOST}"],
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
            ["pkill", "-f", f"ssh.*{LOCAL_PORT}.*{JUMPHOST}"],
            capture_output=True,
            timeout=5
        )
        time.sleep(1)
    except Exception:
        pass

def start_tunnel():
    """Start SSH tunnel in background via jumphost."""
    try:
        # Kill any existing tunnels first
        kill_existing_tunnels()

        # Start new tunnel: local:11434 -> jumphost -> remote:11434
        # ssh -f -N -L 11434:localhost:11434 -J localhost -p 2222 localhost
        result = subprocess.run(
            ["ssh", "-f", "-N",
             "-L", f"{LOCAL_PORT}:localhost:{LOCAL_PORT}",
             "-J", JUMPHOST,
             "-p", REMOTE_PORT,
             REMOTE_HOST],
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
    Ensure Hermes connection is working.
    Returns True if connection is ready, False if failed.
    """

    # Step 1: Check if Ollama is already responding
    if check_ollama_responding():
        if verbose:
            print("✓ Hermes connection already working")
        return True

    if verbose:
        print("⚠ Hermes not responding, checking tunnel...")

    # Step 2: Check if tunnel process exists but not responding
    if check_tunnel_process():
        if verbose:
            print("⚠ Tunnel process exists but Hermes not responding")
            print("  Restarting tunnel...")
        kill_existing_tunnels()

    # Step 3: Start tunnel
    if verbose:
        print(f"→ Starting SSH tunnel via {JUMPHOST} to {REMOTE_HOST}:{REMOTE_PORT}...")

    if not start_tunnel():
        if verbose:
            print("✗ Failed to start SSH tunnel")
        return False

    # Step 4: Verify connection
    time.sleep(1)
    if check_ollama_responding():
        if verbose:
            print("✓ Hermes connection established")
        return True
    else:
        if verbose:
            print("✗ Tunnel started but Hermes still not responding")
            print(f"  (Check if Ollama is running on {SSH_HOST})")
        return False

def main():
    """CLI usage."""
    verbose = "--quiet" not in sys.argv
    success = ensure_connection(verbose=verbose)
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
