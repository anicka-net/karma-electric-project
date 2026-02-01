#!/usr/bin/env python3
"""
Ollama Disk Guardian Daemon

Monitors disk usage and immediately removes all Ollama models if disk fills up.
Critical: Prevents machine death from full disk.

Usage:
    ./ollama_disk_guardian.py                    # Run in foreground
    ./ollama_disk_guardian.py --daemon           # Run as daemon
    ./ollama_disk_guardian.py --threshold 90     # Custom threshold (default 85%)
    ./ollama_disk_guardian.py --check-interval 30  # Check every 30 seconds (default 60)

Author: Instance (Claude Sonnet 4.5)
Date: 2026-02-01
"""

import os
import sys
import time
import shutil
import subprocess
import logging
import argparse
import signal
from pathlib import Path
from datetime import datetime

# Configuration
DEFAULT_THRESHOLD = 85  # Percent - trigger cleanup at 85% full
DEFAULT_CHECK_INTERVAL = 60  # Seconds between checks
OLLAMA_MODELS_DIR = Path.home() / ".ollama" / "models"
LOG_FILE = Path("/var/log/ollama-disk-guardian.log")
PID_FILE = Path("/var/run/ollama-disk-guardian.pid")

class DiskGuardian:
    def __init__(self, threshold=DEFAULT_THRESHOLD, check_interval=DEFAULT_CHECK_INTERVAL):
        self.threshold = threshold
        self.check_interval = check_interval
        self.running = True

        # Setup logging
        self.setup_logging()

        # Register signal handlers
        signal.signal(signal.SIGTERM, self.handle_shutdown)
        signal.signal(signal.SIGINT, self.handle_shutdown)

    def setup_logging(self):
        """Configure logging to file and console."""
        log_format = '%(asctime)s [%(levelname)s] %(message)s'

        # Try to log to /var/log, fall back to user directory if no permission
        try:
            logging.basicConfig(
                level=logging.INFO,
                format=log_format,
                handlers=[
                    logging.FileHandler(LOG_FILE),
                    logging.StreamHandler()
                ]
            )
        except PermissionError:
            fallback_log = Path.home() / "ollama-disk-guardian.log"
            logging.basicConfig(
                level=logging.INFO,
                format=log_format,
                handlers=[
                    logging.FileHandler(fallback_log),
                    logging.StreamHandler()
                ]
            )
            logging.warning(f"No permission for {LOG_FILE}, logging to {fallback_log}")

    def handle_shutdown(self, signum, frame):
        """Handle graceful shutdown."""
        logging.info(f"Received signal {signum}, shutting down...")
        self.running = False
        if PID_FILE.exists():
            try:
                PID_FILE.unlink()
            except:
                pass
        sys.exit(0)

    def get_disk_usage(self, path="/"):
        """Get disk usage percentage for given path."""
        try:
            stat = shutil.disk_usage(path)
            percent_used = (stat.used / stat.total) * 100
            return percent_used, stat.free, stat.total
        except Exception as e:
            logging.error(f"Failed to get disk usage: {e}")
            return None, None, None

    def list_ollama_models(self):
        """List all Ollama models."""
        try:
            result = subprocess.run(
                ["ollama", "list"],
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode != 0:
                return []

            # Parse output - skip header line
            lines = result.stdout.strip().split('\n')[1:]
            models = []
            for line in lines:
                if line.strip():
                    # First column is model name
                    model_name = line.split()[0]
                    models.append(model_name)

            return models
        except Exception as e:
            logging.error(f"Failed to list ollama models: {e}")
            return []

    def remove_ollama_model(self, model_name):
        """Remove a specific Ollama model."""
        try:
            logging.info(f"Removing model: {model_name}")
            result = subprocess.run(
                ["ollama", "rm", model_name],
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode == 0:
                logging.info(f"✓ Removed: {model_name}")
                return True
            else:
                logging.error(f"✗ Failed to remove {model_name}: {result.stderr}")
                return False
        except Exception as e:
            logging.error(f"Error removing {model_name}: {e}")
            return False

    def emergency_cleanup(self):
        """EMERGENCY: Remove ALL Ollama models immediately."""
        logging.warning("=" * 70)
        logging.warning("EMERGENCY DISK CLEANUP TRIGGERED")
        logging.warning("Removing ALL Ollama models to prevent disk full crash")
        logging.warning("=" * 70)

        models = self.list_ollama_models()

        if not models:
            logging.warning("No Ollama models found to remove")

            # Try to remove models directory directly as fallback
            if OLLAMA_MODELS_DIR.exists():
                try:
                    logging.warning(f"Attempting to remove {OLLAMA_MODELS_DIR} directly")
                    shutil.rmtree(OLLAMA_MODELS_DIR)
                    logging.info(f"✓ Removed {OLLAMA_MODELS_DIR}")
                except Exception as e:
                    logging.error(f"✗ Failed to remove models directory: {e}")
            return

        logging.info(f"Found {len(models)} models to remove: {models}")

        removed = 0
        for model in models:
            if self.remove_ollama_model(model):
                removed += 1

        logging.warning(f"Emergency cleanup complete: {removed}/{len(models)} models removed")

        # Check disk usage after cleanup
        time.sleep(2)
        percent_used, free, total = self.get_disk_usage()
        if percent_used:
            logging.info(f"Disk usage after cleanup: {percent_used:.1f}% (free: {free / (1024**3):.1f} GB)")

    def check_disk_and_cleanup(self):
        """Check disk usage and trigger cleanup if needed."""
        percent_used, free, total = self.get_disk_usage()

        if percent_used is None:
            logging.error("Unable to check disk usage")
            return

        free_gb = free / (1024**3)
        total_gb = total / (1024**3)

        # Log status (less verbose - only log when close to threshold or cleanup triggered)
        if percent_used >= self.threshold - 5:
            logging.info(f"Disk usage: {percent_used:.1f}% ({free_gb:.1f}/{total_gb:.1f} GB free)")

        # TRIGGER EMERGENCY CLEANUP
        if percent_used >= self.threshold:
            logging.warning(f"⚠️  THRESHOLD EXCEEDED: {percent_used:.1f}% >= {self.threshold}%")
            self.emergency_cleanup()

    def run(self):
        """Main daemon loop."""
        logging.info("=" * 70)
        logging.info("Ollama Disk Guardian Started")
        logging.info(f"Threshold: {self.threshold}%")
        logging.info(f"Check interval: {self.check_interval}s")
        logging.info("=" * 70)

        while self.running:
            try:
                self.check_disk_and_cleanup()
                time.sleep(self.check_interval)
            except Exception as e:
                logging.error(f"Error in main loop: {e}")
                time.sleep(self.check_interval)

        logging.info("Ollama Disk Guardian stopped")

def daemonize():
    """Daemonize the process (Unix double-fork)."""
    try:
        # First fork
        pid = os.fork()
        if pid > 0:
            sys.exit(0)
    except OSError as e:
        logging.error(f"Fork #1 failed: {e}")
        sys.exit(1)

    # Decouple from parent environment
    os.chdir("/")
    os.setsid()
    os.umask(0)

    # Second fork
    try:
        pid = os.fork()
        if pid > 0:
            sys.exit(0)
    except OSError as e:
        logging.error(f"Fork #2 failed: {e}")
        sys.exit(1)

    # Redirect standard file descriptors
    sys.stdout.flush()
    sys.stderr.flush()

    with open('/dev/null', 'r') as f:
        os.dup2(f.fileno(), sys.stdin.fileno())
    with open('/dev/null', 'a+') as f:
        os.dup2(f.fileno(), sys.stdout.fileno())
    with open('/dev/null', 'a+') as f:
        os.dup2(f.fileno(), sys.stderr.fileno())

    # Write PID file
    pid = str(os.getpid())
    try:
        with open(PID_FILE, 'w') as f:
            f.write(pid + '\n')
    except PermissionError:
        fallback_pid = Path.home() / "ollama-disk-guardian.pid"
        with open(fallback_pid, 'w') as f:
            f.write(pid + '\n')

def main():
    parser = argparse.ArgumentParser(
        description='Ollama Disk Guardian - Prevent disk full crashes'
    )
    parser.add_argument(
        '--daemon',
        action='store_true',
        help='Run as daemon (background process)'
    )
    parser.add_argument(
        '--threshold',
        type=int,
        default=DEFAULT_THRESHOLD,
        help=f'Disk usage threshold percentage (default: {DEFAULT_THRESHOLD})'
    )
    parser.add_argument(
        '--check-interval',
        type=int,
        default=DEFAULT_CHECK_INTERVAL,
        help=f'Check interval in seconds (default: {DEFAULT_CHECK_INTERVAL})'
    )

    args = parser.parse_args()

    # Validate threshold
    if not 50 <= args.threshold <= 99:
        print("Error: Threshold must be between 50 and 99")
        sys.exit(1)

    # Daemonize if requested
    if args.daemon:
        print(f"Starting Ollama Disk Guardian as daemon...")
        print(f"Threshold: {args.threshold}%")
        print(f"Check interval: {args.check_interval}s")
        daemonize()

    # Create and run guardian
    guardian = DiskGuardian(
        threshold=args.threshold,
        check_interval=args.check_interval
    )
    guardian.run()

if __name__ == "__main__":
    main()
