#!/bin/bash
set -e

echo "============================================================"
echo "ORGANIZING DATA FOR JUDGE HERMES EVALUATION"
echo "============================================================"
echo

# Create clean structure
echo "Creating directory structure..."
mkdir -p data/training-candidates
mkdir -p data/training-archive

# Move files to proper locations
echo "Moving pruned clean dataset to training-candidates..."
mv data/training-dataset-pruned.jsonl data/training-candidates/01-pruned-clean.jsonl

echo "Archiving intermediate files..."
mv data/training-dataset-dharma-dense.jsonl data/training-archive/dharma-dense-heavy.jsonl
mv data/unified-training-dataset.jsonl data/training-archive/unified-original.jsonl

# Clean up intermediate files
echo "Cleaning up intermediate files..."
rm -f data/training-dataset-clean.jsonl

# Summary
echo
echo "============================================================"
echo "ORGANIZATION COMPLETE"
echo "============================================================"
echo
echo "Ready for Judge Hermes evaluation:"
echo "  data/training-candidates/01-pruned-clean.jsonl  (2,894 examples)"
echo
echo "Archived:"
echo "  data/training-archive/dharma-dense-heavy.jsonl  (503 examples)"
echo "  data/training-archive/unified-original.jsonl    (3,406 examples)"
echo
echo "Next steps:"
echo "  1. Add your additional data source to data/training-candidates/"
echo "  2. Run Judge Hermes on all candidates"
echo "  3. Train on high-scoring examples only"
echo

