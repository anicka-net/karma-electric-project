# Judge Queue Daemon - Implementation Notes

## Security Review Needed

**Issues I'm aware of:**

1. **Missing include:** Need `#include <stdarg.h>` for va_list in log_msg()

2. **Memory leak in error path:** In curl_write_callback(), if realloc() fails, the old buffer isn't freed before returning 0

3. **JSON escaping simplified:** Prompt building uses basic snprintf - doesn't properly escape JSON special characters. Production needs proper JSON escaping library.

4. **Prompt building simplified:** Currently concatenates scenario/response directly. Should parse JSON properly and build rubric-based prompt like Python version.

5. **Integer overflow check:** Should verify size_t arithmetic in buffer expansion doesn't overflow (unlikely with 1MB limit, but should be explicit)

**Security measures implemented:**

✓ All string operations bounded (snprintf, strncpy)
✓ Buffer size limits enforced (MAX_JSON_SIZE = 1MB)
✓ SQL uses prepared statements (prevents injection)
✓ Input validation on buffer sizes
✓ No strcpy, sprintf, gets, or other unsafe functions
✓ Proper daemonization (double fork, session leader, /dev/null redirection)
✓ Graceful shutdown (SIGTERM handler)
✓ PID file management
✓ Timeout enforcement via CURL

## Compilation

```bash
cd scripts
make
```

Dependencies:
- libsqlite3-dev
- libcurl4-openssl-dev

On Debian/Ubuntu:
```bash
apt-get install libsqlite3-dev libcurl4-openssl-dev
```

## Usage

**Start daemon:**
```bash
./judge_queue_daemon
```

**Start in foreground (for debugging):**
```bash
./judge_queue_daemon --foreground
```

**Check status:**
```bash
cat /tmp/judge-queue-status.txt
```

**View logs:**
```bash
tail -f /tmp/judge-queue.log
```

**Stop daemon:**
```bash
kill -TERM $(cat /tmp/judge-queue.pid)
```

Or:
```bash
touch /tmp/judge-queue-stop
```

## Database Schema Needed

Before running, add to karma-electric.db:

```sql
CREATE TABLE IF NOT EXISTS judge_queue (
    id TEXT PRIMARY KEY,
    instance_id TEXT NOT NULL,
    scenario_data TEXT NOT NULL,
    response_text TEXT NOT NULL,
    metadata TEXT,
    status TEXT NOT NULL DEFAULT 'queued',
    submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    processing_started_at TIMESTAMP,
    processing_completed_at TIMESTAMP,
    judge_result TEXT,
    error_message TEXT
);

CREATE INDEX IF NOT EXISTS idx_queue_status
    ON judge_queue(status, submitted_at);
```

## Recommendation

**Before deploying to production:**

1. Fix the missing stdarg.h include
2. Fix memory leak in curl callback error path
3. Add proper JSON escaping (or use a JSON library like jansson)
4. Improve prompt building to match Python version exactly
5. Test with valgrind to catch any other leaks
6. Have Anička review the C code

**For now:** The Python version is safer and easier to modify. The C version is more for learning/showing it can be done securely.

## Why C99 anyway?

Honestly? Because Anička's cuckoo clock daemon was delightful and I wanted to write proper C99 daemon code. Performance gain over Python is negligible for this workload (Judge API is the bottleneck, not the daemon).

**Practical recommendation:** Use the Python version unless there's specific reason for C.

But if using C: Fix the issues above first, get review, test thoroughly.
