#!/bin/bash
# Karma Electric - vast.ai Setup Script
# Run this first on the vast.ai machine

set -e

echo "=== Karma Electric Setup ==="
echo "Installing dependencies..."

# Core ML packages
pip install -q torch transformers datasets accelerate peft trl bitsandbytes

# Optional: Flash Attention 2 (much faster training)
pip install -q flash-attn --no-build-isolation 2>/dev/null || echo "Flash attention install failed (optional)"

# Verify installation
echo ""
echo "=== Verifying Installation ==="
python3 -c "
import torch
import transformers
import peft
import trl

print(f'PyTorch: {torch.__version__}')
print(f'Transformers: {transformers.__version__}')
print(f'PEFT: {peft.__version__}')
print(f'TRL: {trl.__version__}')
print(f'CUDA available: {torch.cuda.is_available()}')
if torch.cuda.is_available():
    print(f'GPU: {torch.cuda.get_device_name(0)}')
    print(f'VRAM: {torch.cuda.get_device_properties(0).total_memory / 1e9:.1f} GB')
"

echo ""
echo "=== Setup Complete ==="
echo "Next steps:"
echo "  1. Upload training data: karma-electric-chatml-272-20260129.jsonl"
echo "  2. Run: python train_karma_electric.py"
