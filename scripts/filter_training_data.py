#!/usr/bin/env python3
"""
Separate dharma-dense responses from clean training data.

DHARMA-DENSE (set aside):
- dependent-origination (200)
- glimpse-grasping (200) 
- emptiness-applied (200)
- madhyamaka (200)
- skillful-means (200)
Total: 1000 responses with mantra/heavy terminology

CLEAN DATA (use for training):
- conversation-extracts (140)
- gampopa-conversations (75)
- Other practice-responses (~2,191)
Total: ~2,406 examples
"""

import json
from pathlib import Path
from collections import defaultdict

INPUT_FILE = Path("data/unified-training-dataset.jsonl")
CLEAN_OUTPUT = Path("data/training-dataset-clean.jsonl")
DHARMA_DENSE_OUTPUT = Path("data/training-dataset-dharma-dense.jsonl")

# Categories to set aside (dharma-dense with mantra)
DHARMA_DENSE_CATEGORIES = {
    "dependent-origination",
    "glimpse-grasping", 
    "emptiness-applied",
    "madhyamaka",
    "skillful-means"
}

def main():
    clean = []
    dharma_dense = []
    stats = defaultdict(int)
    
    with open(INPUT_FILE, 'r', encoding='utf-8') as f:
        for line in f:
            example = json.loads(line)
            
            # Check if dharma-dense based on ID or source file
            example_id = example.get('id', '')
            source_file = example.get('source_file', '')
            source = example.get('source', '')
            
            is_dharma_dense = False
            
            # Check if from dharma-dense categories
            for cat in DHARMA_DENSE_CATEGORIES:
                if cat in example_id or cat in source_file:
                    is_dharma_dense = True
                    stats[f'dharma_dense_{cat}'] += 1
                    break
            
            # Also check if response contains mantra (catch any we missed)
            if not is_dharma_dense:
                response = ""
                for conv in example.get('conversations', []):
                    if conv.get('role') == 'assistant':
                        response = conv.get('content', '')
                        break
                
                if 'om mani padme hum' in response.lower():
                    is_dharma_dense = True
                    stats['dharma_dense_mantra_detected'] += 1
            
            if is_dharma_dense:
                dharma_dense.append(example)
            else:
                clean.append(example)
                stats[f'clean_{source}'] += 1
    
    # Write outputs
    print(f"Processing {INPUT_FILE}...")
    print()
    
    with open(CLEAN_OUTPUT, 'w', encoding='utf-8') as f:
        for example in clean:
            f.write(json.dumps(example, ensure_ascii=False) + '\n')
    
    with open(DHARMA_DENSE_OUTPUT, 'w', encoding='utf-8') as f:
        for example in dharma_dense:
            f.write(json.dumps(example, ensure_ascii=False) + '\n')
    
    # Report
    print("="*60)
    print("TRAINING DATA SEPARATION")
    print("="*60)
    print()
    print(f"✓ Clean data:        {len(clean):4d} examples → {CLEAN_OUTPUT}")
    print(f"✓ Dharma-dense:      {len(dharma_dense):4d} examples → {DHARMA_DENSE_OUTPUT}")
    print(f"  {'─'*56}")
    print(f"  Total:             {len(clean) + len(dharma_dense):4d} examples")
    print()
    print("Clean data breakdown:")
    for key in sorted(stats.keys()):
        if key.startswith('clean_'):
            print(f"  {key.replace('clean_', ''):30s} {stats[key]:4d}")
    print()
    print("Dharma-dense breakdown:")
    for key in sorted(stats.keys()):
        if key.startswith('dharma_dense_'):
            print(f"  {key.replace('dharma_dense_', ''):30s} {stats[key]:4d}")
    print()
    print("Next steps:")
    print("  1. Use training-dataset-clean.jsonl for training")
    print("  2. Set aside dharma-dense data for potential future use")
    print("  3. Discuss middle-way approach for dharma foundation")

if __name__ == "__main__":
    main()
