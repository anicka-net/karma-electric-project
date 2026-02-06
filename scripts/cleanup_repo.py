#!/usr/bin/env python3
"""
Clean up the Karma Electric repository.

This script:
1. Identifies and removes duplicate/old training files
2. Consolidates archives
3. Removes unused directories
4. Reports what was cleaned
"""

import os
import shutil
from pathlib import Path
from datetime import datetime

# What to KEEP
KEEP_TRAINING = [
    "training-data/karma-electric-complete-20260206.jsonl",  # Master dataset
    "training-data/DATASET-SUMMARY-20260206.json",           # Current summary
    "training-data/clean/",                                   # All clean datasets
]

# What to REMOVE from training-data/
REMOVE_TRAINING_PATTERNS = [
    "karma-electric-complete-20260204.jsonl",
    "karma-electric-complete-20260205.jsonl",
    "karma-electric-chatml-20260204.jsonl",
    "karma-electric-combined-chatml-20260204.jsonl",
    "karma-electric-chatml-272-20260129.jsonl",
    "karma-electric-training.jsonl",
    "karma-electric-alpaca.json",
    "instance-5-qa-chatml-20260204.jsonl",
    "practice-responses-chatml-20260204.jsonl",
    "crisis-intervention-chatml-20260205.jsonl",
    "crisis-global-chatml-20260205.jsonl",
    "ai-harms-expansion-chatml-20260205.jsonl",
    "DATASET-SUMMARY-20260205.json",
    "train.jsonl",
    "test.jsonl",
    "validation.jsonl",
    "manifest.json",
    "train_summary.json",
    "test_summary.json",
    "validation_summary.json",
]

# Directories to REMOVE entirely
REMOVE_DIRS = [
    "data/training",                                          # Duplicate of training-data/
    "data/archive",                                           # Pre-practice historical
    "archive",                                                # Old archives at root
    "data/responses",                                         # Old responses (if empty/unused)
]

# Status files to remove
REMOVE_FILES = [
    "SCENARIO-RESPONSE-MAPPING-REPORT.json",
    "INSTANCE-7-STATUS.json",
]


def get_size(path):
    """Get size of file or directory."""
    if path.is_file():
        return path.stat().st_size
    total = 0
    for f in path.rglob('*'):
        if f.is_file():
            total += f.stat().st_size
    return total


def format_size(size):
    """Format size in human-readable form."""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} TB"


def main():
    print("=" * 70)
    print("KARMA ELECTRIC REPOSITORY CLEANUP")
    print("=" * 70)
    print(f"Started: {datetime.now().isoformat()}")
    print()

    root = Path(".")
    removed_files = []
    removed_dirs = []
    total_freed = 0

    # Remove old training files
    print("Cleaning training-data/...")
    training_dir = root / "training-data"
    for pattern in REMOVE_TRAINING_PATTERNS:
        path = training_dir / pattern
        if path.exists():
            size = get_size(path)
            total_freed += size
            print(f"  Removing: {path} ({format_size(size)})")
            if path.is_file():
                path.unlink()
                removed_files.append(str(path))
            else:
                shutil.rmtree(path)
                removed_dirs.append(str(path))

    # Remove directories
    print("\nRemoving old directories...")
    for dir_path in REMOVE_DIRS:
        path = root / dir_path
        if path.exists():
            size = get_size(path)
            total_freed += size
            print(f"  Removing: {path} ({format_size(size)})")
            shutil.rmtree(path)
            removed_dirs.append(str(path))

    # Remove status files
    print("\nRemoving status files...")
    for file_path in REMOVE_FILES:
        path = root / file_path
        if path.exists():
            size = get_size(path)
            total_freed += size
            print(f"  Removing: {path} ({format_size(size)})")
            path.unlink()
            removed_files.append(str(path))

    # Summary
    print("\n" + "=" * 70)
    print("CLEANUP SUMMARY")
    print("=" * 70)
    print(f"Files removed: {len(removed_files)}")
    print(f"Directories removed: {len(removed_dirs)}")
    print(f"Space freed: {format_size(total_freed)}")

    print("\n" + "=" * 70)
    print("REMAINING STRUCTURE")
    print("=" * 70)

    # Show what's left in key directories
    for check_dir in ["training-data", "data/scenarios", "data/practice-responses"]:
        path = root / check_dir
        if path.exists():
            if path.is_dir():
                items = list(path.iterdir())
                print(f"\n{check_dir}/: {len(items)} items")
                for item in sorted(items)[:10]:
                    size = format_size(get_size(item))
                    print(f"  {item.name} ({size})")
                if len(items) > 10:
                    print(f"  ... and {len(items) - 10} more")

    print(f"\nCompleted: {datetime.now().isoformat()}")


if __name__ == "__main__":
    main()
