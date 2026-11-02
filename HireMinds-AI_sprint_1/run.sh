#!/usr/bin/env bash
# HireMinds AI Launcher for Linux / macOS

# If executed outside a terminal (e.g. double-clicked from file manager), open in terminal emulator
if [ ! -t 0 ] && [ -z "$HIREMINDS_IN_TERMINAL" ]; then
    export HIREMINDS_IN_TERMINAL=1
    for term in x-terminal-emulator qterminal alacritty xterm gnome-terminal konsole; do
        if command -v "$term" >/dev/null 2>&1; then
            exec "$term" -e bash "$0" "$@"
        fi
    done
fi

# Load user environment (nvm, pyenv, bashrc)
[ -f "$HOME/.profile" ] && source "$HOME/.profile" 2>/dev/null
[ -f "$HOME/.bashrc" ] && source "$HOME/.bashrc" 2>/dev/null

# Load NVM and Pyenv if present
if [ -d "$HOME/.config/nvm" ] || [ -d "$HOME/.nvm" ]; then
    export NVM_DIR="${NVM_DIR:-$HOME/.config/nvm}"
    [ -d "$HOME/.nvm" ] && NVM_DIR="$HOME/.nvm"
    [ -s "$NVM_DIR/nvm.sh" ] && source "$NVM_DIR/nvm.sh" 2>/dev/null
fi
if [ -d "$HOME/.pyenv" ]; then
    export PYENV_ROOT="$HOME/.pyenv"
    export PATH="$PYENV_ROOT/bin:$PYENV_ROOT/shims:$PATH"
fi

# Locate project directories
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [ -d "$SCRIPT_DIR/HireMinds-AI_sprint_1/backend" ]; then
    PROJECT_DIR="$SCRIPT_DIR/HireMinds-AI_sprint_1"
elif [ -d "$SCRIPT_DIR/backend" ]; then
    PROJECT_DIR="$SCRIPT_DIR"
else
    echo "[ERROR] Could not locate backend directory."
    read -rp "Press Enter to exit..."
    exit 1
fi

BACKEND_DIR="$PROJECT_DIR/backend"
FRONTEND_DIR="$PROJECT_DIR/frontend"

# Clean up any lingering processes on ports 8000 and 5173
for port in 8000 5173; do
    if command -v lsof >/dev/null 2>&1; then
        PIDS=$(lsof -ti :$port 2>/dev/null)
        if [ -n "$PIDS" ]; then
            echo "[INFO] Freeing port $port (closing stale process $PIDS)..."
            kill -9 $PIDS 2>/dev/null || true
            sleep 1
        fi
    fi
done

# Detect Python interpreter
PYTHON_BIN=""
if [ -f "$BACKEND_DIR/venv/bin/python" ]; then
    PYTHON_BIN="$BACKEND_DIR/venv/bin/python"
elif [ -f "$PROJECT_DIR/venv/bin/python" ]; then
    PYTHON_BIN="$PROJECT_DIR/venv/bin/python"
elif command -v python3 >/dev/null 2>&1; then
    PYTHON_BIN="python3"
else
    echo "[ERROR] Python 3 not found!"
    read -rp "Press Enter to exit..."
    exit 1
fi

# Detect npm
NPM_BIN=""
if command -v npm >/dev/null 2>&1; then
    NPM_BIN="npm"
elif [ -f "$HOME/.config/nvm/versions/node/v24.19.0/bin/npm" ]; then
    NPM_BIN="$HOME/.config/nvm/versions/node/v24.19.0/bin/npm"
    export PATH="$HOME/.config/nvm/versions/node/v24.19.0/bin:$PATH"
else
    echo "[ERROR] npm not found! Please ensure Node.js is installed."
    read -rp "Press Enter to exit..."
    exit 1
fi

echo "==================================================="
echo "             HireMinds AI Launcher"
echo "==================================================="
echo "Project Directory: $PROJECT_DIR"
echo "Python:            $PYTHON_BIN"
echo "Node/npm:          $NPM_BIN"
echo "==================================================="

cleanup() {
    echo ""
    echo "Shutting down HireMinds AI services..."
    [ -n "$BACKEND_PID" ] && kill "$BACKEND_PID" 2>/dev/null
    [ -n "$FRONTEND_PID" ] && kill "$FRONTEND_PID" 2>/dev/null
    for port in 8000 5173; do
        if command -v lsof >/dev/null 2>&1; then
            PIDS=$(lsof -ti :$port 2>/dev/null)
            [ -n "$PIDS" ] && kill -9 $PIDS 2>/dev/null || true
        fi
    done
    exit 0
}

trap cleanup SIGINT SIGTERM EXIT

# Start Backend
echo ""
echo "[1/2] Starting FastAPI Backend on http://127.0.0.1:8000 ..."
cd "$BACKEND_DIR" || exit 1
export PYTHONPATH="$BACKEND_DIR"
"$PYTHON_BIN" -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000 &
BACKEND_PID=$!

# Start Frontend
echo "[2/2] Starting Vite Frontend on http://localhost:5173 ..."
cd "$FRONTEND_DIR" || exit 1
"$NPM_BIN" run dev &
FRONTEND_PID=$!

# Wait for Vite to bind
sleep 3

# Open default browser
if command -v xdg-open > /dev/null 2>&1; then
    xdg-open http://localhost:5173 >/dev/null 2>&1 &
elif command -v open > /dev/null 2>&1; then
    open http://localhost:5173 >/dev/null 2>&1 &
fi

echo ""
echo "==================================================="
echo "HireMinds AI is running!"
echo "- Frontend: http://localhost:5173"
echo "- Backend:  http://127.0.0.1:8000"
echo "- API Docs: http://127.0.0.1:8000/api/v1/docs"
echo "Press Ctrl+C to stop both servers."
echo "==================================================="

wait
