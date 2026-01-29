# Judge Infrastructure Setup

## Overview

The Apertus-70B judge runs on **vast.ai** (rented GPU), managed by Vojtech, and is accessible via SSH tunnel through `localhost`.

## Infrastructure

**Hardware:**
- GPU: 96GB RTX 6000 PRO (rented on vast.ai)
- Service: Ollama
- Access: SSH tunnel via localhost:11434

**Models Available:**
- `MichelRosselli/apertus:70b-instruct-2509-q4_k_m` (primary judge)
- `gpt-oss:120b`
- `gurubot/GLM-4.5-Air-Derestricted:Q4_K_M`
- `nemotron-3-nano:30b`
- `qwen3:14b`

## Connection Setup

### Automatic Connection (Recommended)

**The batch evaluation script now handles connections automatically.** It will:
- Check if connection is working
- Auto-restart SSH tunnel if dead
- Survive laptop sleep/wake cycles

No manual setup needed! Just run:
```bash
python3 scripts/batch_baseline.py
```

### Manual Connection (For Testing)

If you need to manually establish connection:

#### 1. Auto-Restart Script (Handles Everything)

```bash
python3 scripts/ensure_ollama_connection.py
```

This will:
- Check if Ollama is responding
- Kill stale SSH tunnels
- Start new tunnel if needed
- Verify connection works

#### 2. Manual SSH Tunnel (Old Method)

```bash
ssh -f -N -L 11434:localhost:11434 localhost
```

**Explanation:**
- `-f`: Fork to background
- `-N`: No remote command (just tunnel)
- `-L 11434:localhost:11434`: Forward local port 11434 to twilight's localhost:11434

**Note:** Manual tunnels die when laptop sleeps. Use auto-restart instead.

#### 3. Verify Connection

```bash
curl http://localhost:11434/api/tags | python3 -m json.tool
```

Should return list of available models.

#### 4. Test Auto-Recovery

```bash
bash scripts/test_connection_recovery.sh
```

Kills tunnel and verifies auto-restart works.

## Usage in Scripts

Scripts use the Ollama API at `http://localhost:11434` with model name:
```python
MODEL_NAME = "MichelRosselli/apertus:70b-instruct-2509-q4_k_m"
```

## Troubleshooting

### Connection Refused (Auto-Fixed)

**Symptom:**
```
curl: (7) Failed to connect to localhost port 11434
```

**Solution:**
The batch script now handles this automatically. But if you need manual fix:
```bash
python3 scripts/ensure_ollama_connection.py
```

### Laptop Sleep/Wake Issues (Auto-Fixed)

**Problem:** SSH tunnels die when laptop sleeps.

**Old behavior:**
- Close laptop → SSH tunnel dies
- Open laptop → Connection refused errors
- Manual restart required

**New behavior (since 2026-01-26):**
- Close laptop → SSH tunnel dies (still happens)
- Open laptop → Batch script auto-detects and restarts tunnel
- No manual intervention needed

**How it works:**
Before each judge evaluation, the script:
1. Tests if Ollama is responding
2. If not, kills stale tunnels
3. Starts fresh tunnel
4. Verifies connection
5. Proceeds with evaluation

**Test it:**
```bash
bash scripts/test_connection_recovery.sh
```

### Timeouts During Evaluation

**Symptom:**
```
HTTPConnectionPool(host='localhost', port=11434): Read timed out
```

**Possible Causes:**
1. vast.ai instance stopped (contact Vojtech)
2. Model too slow for complex prompts (70B on Q4_K_M quantization)
3. Network issues

**Solution:**
- Increase timeout in script (currently 300s = 5min)
- Check vast.ai instance status with Vojtech
- Consider using smaller model for faster testing

## Cost Management

- vast.ai charges by the hour for GPU rental
- Vojtech manages the instance
- Turn off when not actively evaluating to save costs

## Contact

**Instance Manager:** Vojtech
**Setup Date:** 2026-01-26
**Project:** karma-electric baseline evaluation
