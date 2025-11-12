#!/bin/bash
set -e

echo "🧪 Running QueueCTL Complete Test Suite"

# Setup
source .venv/bin/activate
rm -rf ~/.queuectl

# Test 1: Basic Enqueue
echo "✅ Test 1: Basic Enqueue"
queuectl enqueue '{"command":"echo Test 1"}' > /dev/null
[ $(queuectl list | wc -l) -gt 1 ] && echo "PASS" || echo "FAIL"

# Test 2: Worker Start/Stop
echo "✅ Test 2: Worker Management"
queuectl worker start --count 2 &
sleep 2
WORKER_COUNT=$(queuectl status | grep "Active Workers" | awk '{print $3}')
[ "$WORKER_COUNT" -eq 2 ] && echo "PASS" || echo "FAIL"
queuectl worker stop
sleep 1

# Test 3: Retry Mechanism
echo "✅ Test 3: Retry Mechanism"
queuectl enqueue '{"command":"exit 1","max_retries":1}'
queuectl worker start &
sleep 5
queuectl worker stop
[ $(queuectl dlq list | wc -l) -gt 1 ] && echo "PASS" || echo "FAIL"

# Test 4: Configuration
echo "✅ Test 4: Configuration"
queuectl config set max_retries 10
VALUE=$(queuectl config get max_retries | awk '{print $2}')
[ "$VALUE" -eq 10 ] && echo "PASS" || echo "FAIL"

echo "🎉 All tests completed!"