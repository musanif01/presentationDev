#!/usr/bin/env bash
set -e

echo "=== AI Presentation Maker ==="
echo ""

# Start Ollama if not running
if ! curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
    echo "Starting Ollama..."
    nohup ollama serve </dev/null > /tmp/ollama.log 2>&1 &
    sleep 3
fi

# Start backend
echo "Starting backend (port 8000)..."
pkill -f "uvicorn main:app" 2>/dev/null || true
nohup uvicorn main:app --host 0.0.0.0 --port 8000 > /tmp/backend.log 2>&1 &
sleep 2

# Start frontend
echo "Starting frontend (port 5173)..."
pkill -f "vite" 2>/dev/null || true
nohup npx vite --host 0.0.0.0 --port 5173 > /tmp/frontend.log 2>&1 &

echo ""
echo "Backend:  http://localhost:8000"
echo "Frontend: http://localhost:5173"
echo ""
echo "Logs:"
echo "  ollama:   tail -f /tmp/ollama.log"
echo "  backend:  tail -f /tmp/backend.log"
echo "  frontend: tail -f /tmp/frontend.log"
