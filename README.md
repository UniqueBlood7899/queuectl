# QueueCTL - CLI-based Background Job Queue System

A production-grade job queue system with worker processes, retry mechanisms with exponential backoff, and Dead Letter Queue (DLQ) support.

## Features

✅ CLI-based job queue management
✅ Multiple concurrent worker processes
✅ Exponential backoff retry mechanism
✅ Dead Letter Queue for failed jobs
✅ Persistent storage (survives restarts)
✅ Configurable retry and backoff settings
✅ Graceful worker shutdown
✅ Job state tracking and monitoring

## Installation

### Prerequisites

- Python 3.7 or higher
- pip

### Setup

1. Clone the repository:
```bash
git clone https://github.com/UniqueBlood7899/queuectl
cd queuectl
```

2. Install the package:
```bash
pip install -e .
```

This will install `queuectl` command globally.

## Usage

### Enqueue Jobs

Add a job to the queue:

```bash
queuectl enqueue '{"id":"job1","command":"echo Hello World"}'
queuectl enqueue '{"command":"sleep 5"}'
queuectl enqueue '{"command":"ls -la","max_retries":5}'
```

### Start Workers

Start one worker:
```bash
queuectl worker start
```

Start multiple workers:
```bash
queuectl worker start --count 3
```

Workers will run in the foreground. Press Ctrl+C to stop them gracefully.

### Stop Workers

To stop all running workers:
```bash
queuectl worker stop
```

### Check Status

View queue status and active workers:
```bash
queuectl status
```

Example Output:
```
=== Queue Status ===

Jobs by State:
╒═══════════╤═════════╕
│ State     │   Count │
╞═══════════╪═════════╡
│ pending   │       2 │
│ completed │       5 │
│ failed    │       1 │
│ dead      │       0 │
╘═══════════╧═════════╛

Active Workers: 3
╒════════════╤═══════╤═══════════╕
│ Worker ID  │   PID │ Running   │
╞════════════╪═══════╪═══════════╡
│ abc12345   │  1234 │ ✓         │
╘════════════╧═══════╧═══════════╛
```

### List Jobs

List all jobs:
```bash
queuectl list
```

List jobs by state:
```bash
queuectl list --state pending
queuectl list --state completed
queuectl list --state failed
queuectl list --state dead
```

### Dead Letter Queue (DLQ)

List jobs in DLQ:
```bash
queuectl dlq list
```

Retry a failed job from DLQ:
```bash
queuectl dlq retry <job-id>
```

### Configuration

View all configuration:
```bash
queuectl config get
```

Get specific config value:
```bash
queuectl config get max_retries
```

Set configuration:
```bash
queuectl config set max_retries 5
queuectl config set backoff_base 3
```

Available configuration options:
- `max_retries`: Maximum retry attempts (default: 3)
- `backoff_base`: Base for exponential backoff calculation (default: 2)
- `worker_poll_interval`: Worker polling interval in seconds (default: 1)

## Architecture

### Job Lifecycle

```
┌─────────┐
│ PENDING │ ──────────────┐
└─────────┘               │
     │                    │
     ▼                    │
┌────────────┐            │
│ PROCESSING │            │
└────────────┘            │
     │                    │
     ├─── Success ───▶ ┌───────────┐
     │                 │ COMPLETED │
     │                 └───────────┘
     │
     └─── Failure ───▶ ┌────────┐
                       │ FAILED │
                       └────────┘
                            │
                            ├─── Retry ───▶ (back to PENDING)
                            │
                            └─── Max Retries ───▶ ┌──────┐
                                                  │ DEAD │
                                                  └──────┘
```

### Components

1. **Job** (`job.py`): Job model with state management
2. **Storage** (`storage.py`): File-based persistent storage with locking
3. **Queue Manager** (`queue.py`): Job queue operations
4. **Worker** (`worker.py`): Job processor with retry logic
5. **Config** (`config.py`): Configuration management
6. **CLI** (`cli.py`): Command-line interface

### Data Persistence

Jobs are stored in JSON format at `~/.queuectl/jobs.json`. The storage layer uses file locking to prevent race conditions when multiple workers access the same data.

### Retry Mechanism

Failed jobs are automatically retried with exponential backoff:

- Delay = base^attempts seconds
- Default base = 2
- Default max retries = 3

Example delays:
- Attempt 1: 2^1 = 2 seconds
- Attempt 2: 2^2 = 4 seconds
- Attempt 3: 2^3 = 8 seconds

After max retries, jobs move to the Dead Letter Queue.

### Worker Management

Workers:
- Run as separate processes
- Poll for pending jobs every second (configurable)
- Handle graceful shutdown (finish current job on SIGTERM/SIGINT)
- Prevent duplicate job processing via locking
- Auto-retry failed jobs with backoff

## Testing

### Basic Job Execution

```bash
# Test successful job
queuectl enqueue '{"command":"echo Success"}'
queuectl worker start

# Check status
queuectl status
queuectl list --state completed
```

### Retry Mechanism

```bash
# Test job that fails initially
queuectl enqueue '{"command":"exit 1","max_retries":3}'
queuectl worker start

# Watch it retry with backoff and move to DLQ
queuectl status
queuectl dlq list
```

### Multiple Workers

```bash
# Enqueue multiple jobs
for i in {1..10}; do
  queuectl enqueue "{\"command\":\"sleep $i && echo Job $i\"}"
done

# Start multiple workers
queuectl worker start --count 3

# Watch them process jobs in parallel
queuectl status
```

### Persistence Test

```bash
# Enqueue jobs
queuectl enqueue '{"command":"echo Test"}'

# Check jobs exist
queuectl list

# Restart terminal/system
# Jobs still present
queuectl list
```

### Invalid Command Test

```bash
# Test with non-existent command
queuectl enqueue '{"command":"nonexistent-command"}'
queuectl worker start

# Should retry and eventually move to DLQ
queuectl dlq list
```

## Assumptions & Trade-offs

### Assumptions

1. Jobs are shell commands executed via subprocess
2. Single-machine deployment (not distributed)
3. File-based storage is acceptable for the scale
4. Workers run on the same machine as the queue

### Trade-offs

1. **File-based storage vs Database**: Chose JSON files for simplicity and zero dependencies. For production at scale, consider SQLite or PostgreSQL.

2. **Polling vs Event-driven**: Workers poll for jobs rather than using pub/sub. Simple but less efficient at scale.

3. **Backoff timing**: Simplified backoff implementation retries immediately after delay. In production, store next_retry_at timestamp.

4. **Process-based workers**: Used multiprocessing for true parallelism. Could use threads for I/O-bound tasks.

5. **No distributed locking**: File locks work for single-machine. For distributed systems, use Redis or similar.

## Project Structure

```
queuectl/

├── __init__.py       # Package initialization
├── cli.py            # CLI commands (Click)
├── job.py            # Job model and state
├── queue_manager.py  # Queue manager (renamed from queue.py)
├── worker.py         # Worker implementation
├── storage.py        # File-based storage
├── config.py         # Configuration
├── utils.py          # Utilities
├── setup.py          # Package setup
├── requirements.txt  # Dependencies
└── README.md         # Documentation
```

## Future Enhancements

- Job timeout handling
- Priority queues
- Scheduled/delayed jobs
- Job output logging to files
- Web dashboard
- Metrics and monitoring
- Distributed deployment support
