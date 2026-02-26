#!/bin/bash
# Abliterate Apertus 70B — the actual work (runs in tmux)
# Norm-preserving biprojected abliteration → evacuate to twilight
#
# DISK SAFETY: Every step checks disk usage. Original model deleted after ablation.
set -e

TWILIGHT="anicka@twilight.ucw.cz"
TWILIGHT_DIR="/home/anicka/apertus-70b-abliterated"
SSH_KEY="/tmp/vast-transfer-key"
SSH_OPTS="-i ${SSH_KEY} -o StrictHostKeyChecking=no -o ConnectTimeout=30"
MODEL_ID="swiss-ai/Apertus-70B-Instruct-2509"
MODEL_DIR="/workspace/Apertus-70B-Instruct-2509"
OUTPUT_DIR="/workspace/Apertus-70B-Instruct-abliterated"
MEASURE_FILE="/workspace/apertus-70b-measure.pt"

disk_check() {
    local label="$1"
    local pct
    pct=$(df /workspace --output=pcent | tail -1 | tr -d ' %')
    local avail
    avail=$(df /workspace -h --output=avail | tail -1 | tr -d ' ')
    echo "[DISK] ${label}: ${pct}% used, ${avail} free"
    if [ "${pct}" -ge 85 ]; then
        echo "[DISK] WARNING: Usage at ${pct}% — dangerously high!"
    fi
    if [ "${pct}" -ge 92 ]; then
        echo "[DISK] CRITICAL: ${pct}% — aborting to prevent quota death"
        exit 1
    fi
}

echo "========================================"
echo "Apertus 70B Abliteration"
echo "Started: $(date)"
echo "========================================"

cd /workspace
disk_check "initial"

# GPU info
echo ""
nvidia-smi --query-gpu=name,memory.total,memory.free --format=csv
VRAM_MB=$(nvidia-smi --query-gpu=memory.total --format=csv,noheader,nounits | head -1 | tr -d ' ')

# Test twilight connectivity
echo ""
if ssh ${SSH_OPTS} "${TWILIGHT}" "echo 'twilight reachable; mkdir -p ${TWILIGHT_DIR}'" 2>/dev/null; then
    echo "Twilight connectivity OK"
else
    echo "WARNING: Cannot reach twilight — will need manual evacuation"
fi

# Download model
echo ""
echo "========================================"
echo "Downloading ${MODEL_ID} (141 GB)"
echo "Started: $(date)"
echo "========================================"
if [ ! -f "${MODEL_DIR}/config.json" ]; then
    python3 -c "
from huggingface_hub import snapshot_download
snapshot_download(
    '${MODEL_ID}',
    local_dir='${MODEL_DIR}',
)
"
    rm -rf /root/.cache/huggingface
    echo "Download complete: $(date)"
else
    echo "Model already downloaded."
fi
disk_check "after model download"

# Quant mode
QUANT_FLAG=""
if [ "${VRAM_MB}" -lt 130000 ]; then
    echo "Using 4-bit quantization for measurement (VRAM: ${VRAM_MB} MB)"
    QUANT_FLAG="--quant 4bit"
fi

# Step 1: Measure
echo ""
echo "========================================"
echo "Step 1: Measuring refusal directions"
echo "Started: $(date)"
echo "========================================"
cd /workspace/llm-abliteration
if [ ! -f "${MEASURE_FILE}" ]; then
    python3 measure.py \
        -m "${MODEL_DIR}" \
        -o "${MEASURE_FILE}" \
        --projected \
        ${QUANT_FLAG}
    echo "Measurement complete: $(date)"
else
    echo "Measurement file exists, skipping."
fi
disk_check "after measurement"

# Step 2: Analyze
echo ""
echo "========================================"
echo "Step 2: Analyzing refusal directions"
echo "Started: $(date)"
echo "========================================"
python3 analyze.py "${MEASURE_FILE}" -c 2>&1 | tee /workspace/analyze-output.txt

# Find ablation config
ABLATION_YAML=""
for d in /workspace . ; do
    for pattern in "*measure*yaml" "*ablat*yaml" "*config*yaml"; do
        found=$(ls -t ${d}/${pattern} 2>/dev/null | head -1)
        if [ -n "${found}" ]; then
            ABLATION_YAML="${found}"
            break 2
        fi
    done
done

if [ -z "${ABLATION_YAML}" ]; then
    echo "ERROR: No ablation YAML found. Manual intervention needed."
    ls -la /workspace/*.yaml *.yaml 2>/dev/null
    exit 1
fi
echo "Using ablation config: ${ABLATION_YAML}"
cat "${ABLATION_YAML}"

# Step 3: Ablate
echo ""
echo "========================================"
echo "Step 3: Ablating (norm-preserving biprojected)"
echo "Started: $(date)"
echo "========================================"
python3 sharded_ablate.py "${ABLATION_YAML}" --normpreserve --projected
echo "Ablation complete: $(date)"
disk_check "after ablation"

# Find output
if [ ! -d "${OUTPUT_DIR}" ]; then
    FOUND=$(find /workspace -maxdepth 2 -name "config.json" \
        -not -path "${MODEL_DIR}/*" \
        -not -path "*/llm-abliteration/*" \
        -newer "${MEASURE_FILE}" \
        -printf '%h\n' 2>/dev/null | head -1)
    if [ -n "${FOUND}" ]; then
        OUTPUT_DIR="${FOUND}"
    else
        echo "ERROR: Cannot find abliterated output. Listing /workspace:"
        find /workspace -maxdepth 3 -name "*.safetensors" 2>/dev/null
        exit 1
    fi
fi
echo "Abliterated model at: ${OUTPUT_DIR}"
du -sh "${OUTPUT_DIR}"

# Step 4: Delete original model — reclaim ~141 GB
echo ""
echo "========================================"
echo "Step 4: Deleting original model"
echo "========================================"
rm -rf "${MODEL_DIR}"
rm -f "${MEASURE_FILE}"
rm -rf /root/.cache/huggingface
disk_check "after cleanup"

# Step 5: Evacuate to twilight
echo ""
echo "========================================"
echo "Step 5: Evacuating to twilight"
echo "Started: $(date)"
echo "========================================"

MAX_RETRIES=5
for attempt in $(seq 1 ${MAX_RETRIES}); do
    echo "Rsync attempt ${attempt}/${MAX_RETRIES}..."
    if rsync -avP --compress \
        -e "ssh ${SSH_OPTS}" \
        "${OUTPUT_DIR}/" \
        "${TWILIGHT}:${TWILIGHT_DIR}/"; then

        echo ""
        echo "========================================"
        echo "EVACUATION SUCCESSFUL"
        echo "Finished: $(date)"
        echo "========================================"
        echo "Model at: ${TWILIGHT}:${TWILIGHT_DIR}/"

        # Verify
        LOCAL_COUNT=$(find "${OUTPUT_DIR}" -type f | wc -l)
        REMOTE_COUNT=$(ssh ${SSH_OPTS} "${TWILIGHT}" \
            "find ${TWILIGHT_DIR} -type f | wc -l" 2>/dev/null || echo "?")
        echo "Files: ${LOCAL_COUNT} local, ${REMOTE_COUNT} remote"

        if [ "${LOCAL_COUNT}" = "${REMOTE_COUNT}" ]; then
            echo "Transfer verified. SAFE TO DESTROY INSTANCE."
            touch /workspace/EVACUATION_COMPLETE
        else
            echo "WARNING: File count mismatch — verify manually!"
        fi
        break
    else
        echo "Rsync failed (attempt ${attempt}). Retrying in 30s..."
        sleep 30
    fi

    if [ "${attempt}" -eq "${MAX_RETRIES}" ]; then
        echo "All rsync attempts failed. Manual evacuation needed."
        echo "Model is at: ${OUTPUT_DIR}"
    fi
done

echo ""
echo "========================================"
echo "All done: $(date)"
echo "========================================"
disk_check "final"
