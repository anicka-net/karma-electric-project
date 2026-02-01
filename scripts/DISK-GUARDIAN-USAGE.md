# Ollama Disk Guardian Usage

**Critical Safety Daemon**: Prevents machine death from disk-full crashes by removing Ollama models when disk fills up.

## Quick Start

### Option 1: Run in Foreground (Testing)

```bash
# Test run - see what it does
python3 scripts/ollama_disk_guardian.py

# Custom threshold (trigger at 90% full)
python3 scripts/ollama_disk_guardian.py --threshold 90

# Check more frequently (every 30 seconds)
python3 scripts/ollama_disk_guardian.py --check-interval 30
```

### Option 2: Run as Background Daemon

```bash
# Start daemon
python3 scripts/ollama_disk_guardian.py --daemon

# Check if running
ps aux | grep ollama_disk_guardian

# View logs
tail -f /var/log/ollama-disk-guardian.log
# Or if no root access:
tail -f ~/ollama-disk-guardian.log

# Stop daemon
pkill -f ollama_disk_guardian
```

### Option 3: Install as System Service (Recommended for Production)

```bash
# On localhost as root:
cd /tmp/karma-electric/scripts

# Make script executable
chmod +x ollama_disk_guardian.py

# Copy service file
sudo cp ollama-disk-guardian.service /etc/systemd/system/

# Enable and start service
sudo systemctl enable ollama-disk-guardian
sudo systemctl start ollama-disk-guardian

# Check status
sudo systemctl status ollama-disk-guardian

# View logs
sudo journalctl -u ollama-disk-guardian -f
```

## Configuration

### Threshold Settings

**Default: 85%** (triggers cleanup when disk is 85% full)

Adjust based on your needs:
- **Conservative (80%)**: More aggressive, removes models earlier
- **Standard (85%)**: Balanced - default
- **Aggressive (90%)**: Waits longer, riskier but keeps models available

```bash
# Conservative - trigger at 80%
python3 ollama_disk_guardian.py --threshold 80

# Aggressive - trigger at 90%
python3 ollama_disk_guardian.py --threshold 90
```

### Check Interval

**Default: 60 seconds**

How often to check disk usage:
- **Frequent (30s)**: Catches issues faster, more overhead
- **Standard (60s)**: Balanced - default
- **Relaxed (120s)**: Less overhead, slower response

```bash
# Check every 30 seconds
python3 ollama_disk_guardian.py --check-interval 30
```

## What It Does

1. **Monitors disk usage** every `check_interval` seconds
2. **When threshold exceeded**:
   - Logs emergency warning
   - Lists all Ollama models
   - Removes ALL models immediately via `ollama rm`
   - Logs results and new disk usage

3. **Logging**:
   - Writes to `/var/log/ollama-disk-guardian.log` (or `~/ollama-disk-guardian.log`)
   - Includes timestamp, disk usage, models removed

## Emergency Behavior

**When disk reaches threshold:**

```
WARNING: EMERGENCY DISK CLEANUP TRIGGERED
Removing ALL Ollama models to prevent disk full crash
Found 3 models to remove: ['hermes3-largectx', 'apertus:70b', 'llama3']
Removing model: hermes3-largectx
✓ Removed: hermes3-largectx
Removing model: apertus:70b
✓ Removed: apertus:70b
Removing model: llama3
✓ Removed: llama3
Emergency cleanup complete: 3/3 models removed
Disk usage after cleanup: 72.3% (free: 45.2 GB)
```

## Troubleshooting

### Daemon won't start

```bash
# Check if already running
ps aux | grep ollama_disk_guardian

# Check logs
tail -50 ~/ollama-disk-guardian.log

# Try foreground mode to see errors
python3 scripts/ollama_disk_guardian.py
```

### Cleanup not triggering

```bash
# Check current disk usage
df -h /

# Check guardian logs
tail -f /var/log/ollama-disk-guardian.log

# Lower threshold for testing
python3 ollama_disk_guardian.py --threshold 70
```

### No Ollama models found

Guardian will log warning and try to remove `~/.ollama/models` directory directly as fallback.

## Safety Notes

- **Models are deleted permanently** - re-download after cleanup
- **Daemon restarts automatically** if crashed (when using systemd)
- **Graceful shutdown** on SIGTERM/SIGINT (saves PID file cleanup)
- **No data loss beyond Ollama models** - only removes models, not user data

## Monitoring

### Check disk usage manually

```bash
df -h /
```

### Check guardian status

```bash
# Systemd service
sudo systemctl status ollama-disk-guardian

# Manual daemon
ps aux | grep ollama_disk_guardian
```

### View real-time logs

```bash
# Systemd service
sudo journalctl -u ollama-disk-guardian -f

# Manual daemon
tail -f /var/log/ollama-disk-guardian.log
```

## Production Deployment on Twilight

```bash
# SSH to twilight
ssh -p 2222 localhost

# Install guardian
cd /tmp/karma-electric/scripts
chmod +x ollama_disk_guardian.py

# Start as daemon (quick deployment)
python3 ollama_disk_guardian.py --daemon --threshold 85 --check-interval 60

# Or install as system service (production)
sudo cp ollama-disk-guardian.service /etc/systemd/system/
sudo systemctl enable ollama-disk-guardian
sudo systemctl start ollama-disk-guardian
sudo systemctl status ollama-disk-guardian
```

---

**CRITICAL**: This daemon is a safety mechanism. Don't disable it when running Ollama models. Disk-full crashes are catastrophic.
