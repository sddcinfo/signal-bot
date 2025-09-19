#!/bin/bash
# Restore script for this snapshot

echo "Restoring from backup..."

# Stop services
../manage.sh stop

# Restore files
cp -r * ../

# Restart services
cd ..
./manage.sh start

echo "Restore complete!"
echo "Run './check_status.sh' to verify"
