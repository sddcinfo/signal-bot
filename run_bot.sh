#!/bin/bash
# Signal Bot Launcher - Unified launcher with virtual environment support

set -e  # Exit on any error

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Function to check for existing bot processes
check_existing_processes() {
    # Look for signal_bot.py processes
    local bot_pids=$(pgrep -f "signal_bot\.py" 2>/dev/null || true)
    # Also check for processes using port 8084
    local port_pid=$(lsof -t -i:8084 2>/dev/null || true)

    if [[ -n "$bot_pids" || -n "$port_pid" ]]; then
        echo "Found existing Signal Bot processes:"

        if [[ -n "$bot_pids" ]]; then
            echo "Bot processes (PIDs): $bot_pids"
        fi

        if [[ -n "$port_pid" ]]; then
            echo "Process using port 8084 (PID): $port_pid"
        fi

        echo

        # Check for --force flag for non-interactive mode
        if [[ "$1" == "--force" ]]; then
            echo "Force mode enabled, stopping existing processes..."
            REPLY="y"
        else
            read -p "Do you want to stop the existing processes and continue? (y/N): " -r
        fi

        if [[ $REPLY =~ ^[Yy]$ ]]; then
            echo "Stopping existing processes..."

            # Kill bot processes
            if [[ -n "$bot_pids" ]]; then
                kill -TERM $bot_pids 2>/dev/null || true
                sleep 2
                kill -KILL $bot_pids 2>/dev/null || true
            fi

            # Kill port processes (if different)
            if [[ -n "$port_pid" && ! "$bot_pids" =~ "$port_pid" ]]; then
                kill -TERM $port_pid 2>/dev/null || true
                sleep 2
                kill -KILL $port_pid 2>/dev/null || true
            fi

            sleep 1
            echo "Existing processes stopped."
        else
            echo "Aborted. Use './run_bot.sh --force' to automatically stop existing processes."
            exit 1
        fi
    fi
}

# Check if virtual environment exists, if not create it
if [[ ! -d "$SCRIPT_DIR/venv" ]]; then
    echo "Virtual environment not found. Creating virtual environment..."
    python3 -m venv "$SCRIPT_DIR/venv"

    if [[ ! -f "$SCRIPT_DIR/requirements.txt" ]]; then
        echo "Error: requirements.txt not found"
        exit 1
    fi

    echo "Installing dependencies..."
    source "$SCRIPT_DIR/venv/bin/activate"
    pip install --upgrade pip
    pip install -r "$SCRIPT_DIR/requirements.txt"
    echo "Virtual environment setup complete."
fi

# Activate virtual environment
source "$SCRIPT_DIR/venv/bin/activate"

# Check for existing processes
check_existing_processes "$1"

# Filter out --force from arguments passed to signal_bot.py
bot_args=()
for arg in "$@"; do
    if [[ "$arg" != "--force" ]]; then
        bot_args+=("$arg")
    fi
done

# Function to handle cleanup on exit
cleanup() {
    echo
    echo "Shutting down Signal Bot..."
    if [[ -n "$BOT_PID" ]]; then
        kill -TERM "$BOT_PID" 2>/dev/null || true
        wait "$BOT_PID" 2>/dev/null || true
    fi
    echo "Signal Bot stopped."
    exit 0
}

# Set up signal handlers for graceful shutdown
trap cleanup SIGINT SIGTERM

echo "Starting Signal Bot..."
echo "Working directory: $SCRIPT_DIR"
echo "Virtual environment: $SCRIPT_DIR/venv"
echo "Web interface will be available at: http://localhost:8084"
echo "Press Ctrl+C to stop"

# Run the bot in background and capture its PID
"$SCRIPT_DIR/signal_bot.py" "${bot_args[@]}" &
BOT_PID=$!

echo "Signal Bot started with PID: $BOT_PID"

# Wait for the bot process to finish
wait "$BOT_PID"