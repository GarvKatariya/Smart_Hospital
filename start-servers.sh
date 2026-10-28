#!/bin/bash

# Smart Hospital Management System - Server Startup Script
# Run this script from your Mac terminal to start both frontend and backend

PROJECT_DIR="/Users/garvkatariya/.gemini/antigravity/scratch/smart-hospital-management-system"
BACKEND_ONLY=false
[ "${1:-}" = "backend-only" ] && BACKEND_ONLY=true

# Prefer a Python environment that can run real OCR. A previous server was
# started with Python 3.14, where PaddleOCR was unavailable, so uploads silently
# returned demo text. HOSPITAL_PYTHON can explicitly select another interpreter.
PYTHON_BIN="${HOSPITAL_PYTHON:-}"
if [ -n "$PYTHON_BIN" ]; then
    if ! "$PYTHON_BIN" -c "import paddleocr" >/dev/null 2>&1; then
        echo "HOSPITAL_PYTHON=$PYTHON_BIN cannot import paddleocr; refusing to start with mock OCR."
        exit 1
    fi
else
    for candidate in "$(command -v python3 2>/dev/null)" "$HOME/anaconda3/bin/python" "$HOME/miniconda3/bin/python" /opt/anaconda3/bin/python; do
        [ -n "$candidate" ] && [ -x "$candidate" ] || continue
        if "$candidate" -c "import paddleocr" >/dev/null 2>&1; then
            PYTHON_BIN="$candidate"
            break
        fi
    done
    if [ -z "$PYTHON_BIN" ]; then
        echo "No Python interpreter with PaddleOCR was found. Install backend/requirements.txt in a supported Python environment, or set HOSPITAL_PYTHON."
        exit 1
    fi
fi

echo "🏥 Starting Smart Hospital Management System..."
echo "================================================"

# Check if backend dependencies are installed
echo ""
echo "📦 Checking backend dependencies..."
cd "$PROJECT_DIR/backend"

if ! "$PYTHON_BIN" -c "import fastapi" 2>/dev/null; then
    echo "Installing backend dependencies (this may take a few minutes)..."
    "$PYTHON_BIN" -m pip install -r requirements.txt
else
    echo "✓ Backend dependencies already installed"
fi

echo "✓ Using OCR-capable Python: $PYTHON_BIN"

# Start backend server in background
echo ""
echo "🚀 Starting backend server on http://localhost:8000..."
cd "$PROJECT_DIR/backend"
"$PYTHON_BIN" -m uvicorn app.main:app --reload --port 8000 > /tmp/hospital-backend.log 2>&1 &
BACKEND_PID=$!
echo "Backend PID: $BACKEND_PID"

# Wait for backend to be ready
echo "Waiting for backend to start..."
sleep 3

if [ "$BACKEND_ONLY" = false ]; then
    # Check if frontend dependencies are installed
    echo ""
    echo "📦 Checking frontend dependencies..."
    cd "$PROJECT_DIR/frontend"

    if [ ! -d "node_modules" ]; then
        echo "Installing frontend dependencies (this may take a few minutes)..."
        npm install
    else
        echo "✓ Frontend dependencies already installed"
    fi

    # Start frontend server in background
    echo ""
    echo "🚀 Starting frontend server on http://localhost:3000..."
    npm run dev > /tmp/hospital-frontend.log 2>&1 &
    FRONTEND_PID=$!
    echo "Frontend PID: $FRONTEND_PID"
fi

echo ""
echo "================================================"
if [ "$BACKEND_ONLY" = false ]; then
    echo "✅ Both servers are starting!"
else
    echo "✅ Backend server is starting!"
fi
echo ""
if [ "$BACKEND_ONLY" = false ]; then
    echo "Frontend: http://localhost:3000"
fi
echo "Backend:  http://localhost:8000"
echo "API Docs: http://localhost:8000/docs"
echo ""
echo "Logs:"
echo "  Backend:  tail -f /tmp/hospital-backend.log"
if [ "$BACKEND_ONLY" = false ]; then
    echo "  Frontend: tail -f /tmp/hospital-frontend.log"
fi
echo ""
echo "To stop the servers:"
if [ "$BACKEND_ONLY" = false ]; then
    echo "  kill $BACKEND_PID $FRONTEND_PID"
else
    echo "  kill $BACKEND_PID"
fi
echo ""
echo "Or save these PIDs:"
echo "  echo $BACKEND_PID > /tmp/hospital-backend.pid"
if [ "$BACKEND_ONLY" = false ]; then
    echo "  echo $FRONTEND_PID > /tmp/hospital-frontend.pid"
fi
echo "================================================"
