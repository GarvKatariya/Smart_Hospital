#!/bin/bash

# Smart Hospital Management System - Server Startup Script
# Run this script from your Mac terminal to start both frontend and backend

PROJECT_DIR="/Users/garvkatariya/.gemini/antigravity/scratch/smart-hospital-management-system"

echo "🏥 Starting Smart Hospital Management System..."
echo "================================================"

# Check if backend dependencies are installed
echo ""
echo "📦 Checking backend dependencies..."
cd "$PROJECT_DIR/backend"

if ! python3 -c "import fastapi" 2>/dev/null; then
    echo "Installing backend dependencies (this may take a few minutes)..."
    pip3 install -r requirements.txt
else
    echo "✓ Backend dependencies already installed"
fi

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

# Start backend server in background
echo ""
echo "🚀 Starting backend server on http://localhost:8000..."
cd "$PROJECT_DIR/backend"
python3 -m uvicorn app.main:app --reload --port 8000 > /tmp/hospital-backend.log 2>&1 &
BACKEND_PID=$!
echo "Backend PID: $BACKEND_PID"

# Wait for backend to be ready
echo "Waiting for backend to start..."
sleep 3

# Start frontend server in background
echo ""
echo "🚀 Starting frontend server on http://localhost:3000..."
cd "$PROJECT_DIR/frontend"
npm run dev > /tmp/hospital-frontend.log 2>&1 &
FRONTEND_PID=$!
echo "Frontend PID: $FRONTEND_PID"

echo ""
echo "================================================"
echo "✅ Both servers are starting!"
echo ""
echo "Frontend: http://localhost:3000"
echo "Backend:  http://localhost:8000"
echo "API Docs: http://localhost:8000/docs"
echo ""
echo "Logs:"
echo "  Backend:  tail -f /tmp/hospital-backend.log"
echo "  Frontend: tail -f /tmp/hospital-frontend.log"
echo ""
echo "To stop the servers:"
echo "  kill $BACKEND_PID $FRONTEND_PID"
echo ""
echo "Or save these PIDs:"
echo "  echo $BACKEND_PID > /tmp/hospital-backend.pid"
echo "  echo $FRONTEND_PID > /tmp/hospital-frontend.pid"
echo "================================================"
