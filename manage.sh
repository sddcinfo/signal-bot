#!/bin/bash
# Enhanced management script with comprehensive DEBUG logging
# Provides backward compatibility and advanced debugging features

# Configuration
DEBUG_LOG="signal_bot_debug.log"
DEBUG_MODE=0
DEBUG_ENV=""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
MAGENTA='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Function to print debug header
print_debug_header() {
    echo "=================================================================================" >> "$DEBUG_LOG"
    echo "DEBUG SESSION STARTED: $(date '+%Y-%m-%d %H:%M:%S.%N')" >> "$DEBUG_LOG"
    echo "Command: $0 $@" >> "$DEBUG_LOG"
    echo "User: $(whoami)" >> "$DEBUG_LOG"
    echo "Working Directory: $(pwd)" >> "$DEBUG_LOG"
    echo "Process ID: $$" >> "$DEBUG_LOG"
    echo "=================================================================================" >> "$DEBUG_LOG"
}

# Function to setup comprehensive debug environment
setup_debug_env() {
    # Python debugging (application level only, not import verbose)
    # export PYTHONVERBOSE=1  # Commenting out - too verbose with imports
    export PYTHONDEBUG=1
    export PYTHONTRACEMALLOC=1  # Reduced from 10 to save memory
    export PYTHONWARNINGS="default"
    export PYTHONFAULTHANDLER=1

    # Application-level debug flags
    export SIGNAL_BOT_DEBUG=1
    export SIGNAL_BOT_LOG_LEVEL="DEBUG"
    export SIGNAL_BOT_TRACE=1
    export SIGNAL_BOT_VERBOSE=1

    # Database debugging
    export SIGNAL_BOT_SQL_DEBUG=1
    export SIGNAL_BOT_SQL_ECHO=1

    # Web server debugging
    export WEB_SERVER_DEBUG=1
    export WEB_SERVER_TRACE=1
    export FLASK_ENV="development"
    export FLASK_DEBUG=1

    # Signal service debugging
    export SIGNAL_SERVICE_DEBUG=1
    export SIGNAL_SERVICE_TRACE=1
    export SIGNAL_CLI_DEBUG=1

    # RPC debugging
    export SIGNAL_RPC_DEBUG=1
    export SIGNAL_RPC_TRACE=1

    # AI service debugging
    export AI_SERVICE_DEBUG=1
    export AI_SERVICE_TRACE=1

    # Network debugging
    export SIGNAL_BOT_NET_DEBUG=1
    export CURL_VERBOSE=1

    # System-level debugging
    export MALLOC_CHECK_=3
    export MALLOC_TRACE="malloc_trace.log"

    # Logging configuration
    export LOG_FORMAT="%(asctime)s.%(msecs)03d [%(process)d:%(thread)d] %(name)s.%(funcName)s:%(lineno)d %(levelname)s: %(message)s"
    export LOG_DATE_FORMAT="%Y-%m-%d %H:%M:%S"

    DEBUG_ENV="PYTHONDEBUG=1 PYTHONTRACEMALLOC=1 PYTHONWARNINGS=default PYTHONFAULTHANDLER=1 SIGNAL_BOT_DEBUG=1 SIGNAL_BOT_LOG_LEVEL=DEBUG SIGNAL_BOT_TRACE=1 SIGNAL_BOT_VERBOSE=1 SIGNAL_BOT_SQL_DEBUG=1 SIGNAL_BOT_SQL_ECHO=1 WEB_SERVER_DEBUG=1 WEB_SERVER_TRACE=1 FLASK_ENV=development FLASK_DEBUG=1 SIGNAL_SERVICE_DEBUG=1 SIGNAL_SERVICE_TRACE=1 SIGNAL_CLI_DEBUG=1 SIGNAL_RPC_DEBUG=1 SIGNAL_RPC_TRACE=1 AI_SERVICE_DEBUG=1 AI_SERVICE_TRACE=1 SIGNAL_BOT_NET_DEBUG=1"
}

# Function to wrap command with debug logging
debug_exec() {
    local cmd="$1"
    echo -e "${CYAN}[DEBUG EXEC]${NC} Running: $cmd" | tee -a "$DEBUG_LOG"
    echo "[$(date '+%Y-%m-%d %H:%M:%S.%N')] COMMAND: $cmd" >> "$DEBUG_LOG"

    # Execute with full debug output captured
    eval "$cmd" 2>&1 | while IFS= read -r line; do
        echo "$line"
        echo "[$(date '+%Y-%m-%d %H:%M:%S.%N')] $line" >> "$DEBUG_LOG"
    done

    local exit_code=${PIPESTATUS[0]}
    echo "[$(date '+%Y-%m-%d %H:%M:%S.%N')] EXIT CODE: $exit_code" >> "$DEBUG_LOG"
    return $exit_code
}

# Function to monitor component logs
monitor_debug_logs() {
    echo -e "${YELLOW}[DEBUG MONITOR]${NC} Starting log aggregation..." | tee -a "$DEBUG_LOG"

    # Create background process to aggregate logs
    (
        tail -F signal_service.log web_server.log signal_bot.log signal_daemon.log 2>/dev/null | \
        while IFS= read -r line; do
            echo "[LOG] $line" >> "$DEBUG_LOG"
        done
    ) &

    MONITOR_PID=$!
    echo "Log monitor PID: $MONITOR_PID" >> "$DEBUG_LOG"
}

# Parse arguments for DEBUG mode
ORIGINAL_ARGS="$@"
ARGS=""
for arg in "$@"; do
    case "$arg" in
        DEBUG|--debug|-d|--DEBUG)
            DEBUG_MODE=1
            echo -e "${MAGENTA}====== DEBUG MODE ENABLED ======${NC}"
            ;;
        *)
            ARGS="$ARGS $arg"
            ;;
    esac
done

# Setup debug environment if enabled
if [ $DEBUG_MODE -eq 1 ]; then
    print_debug_header "$ORIGINAL_ARGS"
    setup_debug_env

    echo -e "${GREEN}Debug Configuration:${NC}"
    echo "  Log File: $DEBUG_LOG"
    echo "  Application Debug: ON"
    echo "  SQL Debug: ON"
    echo "  Trace Enabled: ON"
    echo "  Memory Tracking: ON"
    echo "  All Services: DEBUG Level"
    echo ""

    # Start log monitor
    monitor_debug_logs

    # Add debug flag to Python invocation
    ARGS="$ARGS --debug"
fi

# Handle special commands
case "$1" in
    debug-status)
        echo -e "${CYAN}=== Debug Status ===${NC}"
        echo "Debug Log: $DEBUG_LOG"
        if [ -f "$DEBUG_LOG" ]; then
            echo "Log Size: $(du -h "$DEBUG_LOG" | cut -f1)"
            echo "Log Lines: $(wc -l < "$DEBUG_LOG")"
            echo ""
            echo "Last 10 entries:"
            tail -10 "$DEBUG_LOG"
        else
            echo "No debug log found"
        fi
        exit 0
        ;;
    debug-clean)
        echo -e "${YELLOW}Cleaning debug logs...${NC}"
        rm -f "$DEBUG_LOG" malloc_trace.log
        echo "Debug logs cleaned"
        exit 0
        ;;
    debug-tail)
        if [ -f "$DEBUG_LOG" ]; then
            tail -f "$DEBUG_LOG"
        else
            echo "No debug log found"
        fi
        exit 0
        ;;
esac

# Automatically add --daemon flag for start/restart commands
if [[ "$1" == "start" ]] || [[ "$1" == "restart" ]]; then
    if [[ ! "$ARGS" == *"--daemon"* ]]; then
        ARGS="$ARGS --daemon"
    fi
fi

# Prepare Python command
if [ -f "venv/bin/python" ]; then
    PYTHON_CMD="venv/bin/python"
else
    PYTHON_CMD="python3"
fi

# Add debug Python flags in debug mode (application-level debugging only)
if [ $DEBUG_MODE -eq 1 ]; then
    # Don't add -v flag, just development mode and warnings
    PYTHON_CMD="$PYTHON_CMD -X dev -W default"
fi

# Execute with or without debug wrapper
if [ $DEBUG_MODE -eq 1 ]; then
    echo -e "${BLUE}Executing with DEBUG wrapper...${NC}"
    debug_exec "$PYTHON_CMD manage.py $ARGS"
    EXIT_CODE=$?

    # Kill monitor on exit
    if [ ! -z "$MONITOR_PID" ]; then
        kill $MONITOR_PID 2>/dev/null
    fi

    echo ""
    echo -e "${GREEN}Debug session complete. Log saved to: $DEBUG_LOG${NC}"
    echo "View with: ./manage.sh debug-tail"

    exit $EXIT_CODE
else
    exec $PYTHON_CMD manage.py $ARGS
fi