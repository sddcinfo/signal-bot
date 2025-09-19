#!/bin/bash
#
# Signal Bot Automated Backup Script
# Add to cron for regular backups:
#
# Daily at 2 AM - Critical backup (messages/attachments only)
# 0 2 * * * /path/to/signal-bot/backup_scheduler.sh daily
#
# Weekly on Sunday at 3 AM - Full backup
# 0 3 * * 0 /path/to/signal-bot/backup_scheduler.sh weekly
#
# Monthly on 1st at 4 AM - Archive old data + Full backup
# 0 4 1 * * /path/to/signal-bot/backup_scheduler.sh monthly

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

# Use virtual environment if it exists
if [ -f "venv/bin/python" ]; then
    PYTHON="venv/bin/python"
else
    PYTHON="python3"
fi

# Log function
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >> backups/backup.log
    echo "$1"
}

# Create backup directory if it doesn't exist
mkdir -p backups/db

case "$1" in
    daily)
        log "Starting daily backup (critical data only)"

        # Create incremental backup of last 24 hours
        $PYTHON db_manager.py backup incremental --hours 24

        # Keep only last 7 daily backups
        $PYTHON db_manager.py rotate --keep-daily 7 --keep-weekly 4 --keep-monthly 6

        log "Daily backup complete"
        ;;

    weekly)
        log "Starting weekly backup (full)"

        # Create full compressed backup
        $PYTHON db_manager.py backup full

        # Optimize database (compress old attachments)
        $PYTHON db_manager.py optimize --compress-attachments --days 30

        # Vacuum to reclaim space
        $PYTHON db_manager.py optimize --vacuum

        log "Weekly backup and optimization complete"
        ;;

    monthly)
        log "Starting monthly maintenance"

        # Archive data older than 180 days
        $PYTHON db_manager.py archive --days 180

        # Create full backup after archiving
        $PYTHON db_manager.py backup full

        # Create critical backup as well (for extra safety)
        $PYTHON db_manager.py backup critical

        # Aggressive optimization
        $PYTHON db_manager.py optimize --compress-attachments --days 7
        $PYTHON db_manager.py optimize --vacuum

        # Rotate old backups
        $PYTHON db_manager.py rotate --keep-daily 7 --keep-weekly 4 --keep-monthly 12

        log "Monthly maintenance complete"
        ;;

    test)
        log "Testing backup system"

        # Run analysis
        echo "=== Database Analysis ==="
        $PYTHON db_manager.py analyze

        echo -e "\n=== Current Backups ==="
        $PYTHON db_manager.py list

        echo -e "\n=== Creating test backup ==="
        $PYTHON db_manager.py backup critical

        echo -e "\n=== Updated backup list ==="
        $PYTHON db_manager.py list

        log "Test complete"
        ;;

    *)
        echo "Signal Bot Backup Scheduler"
        echo ""
        echo "Usage: $0 {daily|weekly|monthly|test}"
        echo ""
        echo "Schedule with cron:"
        echo "  Daily:   0 2 * * * $SCRIPT_DIR/backup_scheduler.sh daily"
        echo "  Weekly:  0 3 * * 0 $SCRIPT_DIR/backup_scheduler.sh weekly"
        echo "  Monthly: 0 4 1 * * $SCRIPT_DIR/backup_scheduler.sh monthly"
        echo ""
        echo "Or add to manage.py:"
        echo "  ./manage backup daily"
        ;;
esac