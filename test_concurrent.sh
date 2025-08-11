#!/bin/bash
# Test concurrent nudge requests

echo "Testing concurrent nudge requests..."

# Send 3 requests in parallel
curl -X POST http://localhost:8000/nudge/send \
  -H "Content-Type: application/json" \
  -d '{"message": "Concurrent test 1", "urgency": "low"}' &

curl -X POST http://localhost:8000/nudge/send \
  -H "Content-Type: application/json" \
  -d '{"message": "Concurrent test 2", "urgency": "normal"}' &

curl -X POST http://localhost:8000/nudge/send \
  -H "Content-Type: application/json" \
  -d '{"message": "Concurrent test 3", "urgency": "high"}' &

# Wait for all background jobs to complete
wait

echo "All concurrent requests completed"