# Signal Bot Troubleshooting Guide

## Quick Diagnostics

Run these commands first to identify issues:

```bash
# Check service status
./manage.sh status

# Validate configuration
./manage.sh config

# Test module loading
./manage.sh test

# View recent logs
./manage.sh logs
```

## Common Issues and Solutions

### Service Issues

#### Bot Not Starting

**Symptoms:**
- Services fail to start
- Process exits immediately
- No web interface available

**Solutions:**

1. Check for existing processes:
```bash
./check_status.sh
pkill -f 'signal_service.py|web_server.py'
```

2. Verify Signal CLI installation:
```bash
which signal-cli
signal-cli --version
```

3. Check database permissions:
```bash
ls -la signal_bot.db
chmod 644 signal_bot.db
```

4. Review error logs:
```bash
tail -50 signal_service.log
tail -50 web_server.log
```

---

#### Port Already in Use

**Error:**
```
[Errno 98] Address already in use
```

**Solutions:**

1. Find and kill process using port:
```bash
lsof -i:8084
kill -9 <PID>
```

2. Use the restart script (auto-kills):
```bash
./restart.sh
```

3. Use alternate port for testing:
```bash
./run_web_server.sh --testing  # Uses port 8085
```

---

#### Web Interface Not Accessible

**Symptoms:**
- Can't connect to http://localhost:8084
- Connection refused errors
- Page doesn't load

**Solutions:**

1. Check if web server is running:
```bash
ps aux | grep web_server.py
netstat -tulpn | grep 8084
```

2. Verify network binding:
```bash
# Should show 0.0.0.0:8084 for network access
./check_status.sh
```

3. Check firewall rules:
```bash
sudo ufw status
sudo ufw allow 8084/tcp
```

4. Test locally first:
```bash
curl http://localhost:8084/api/status
```

---

### Signal CLI Issues

#### Device Not Linked

**Symptoms:**
- No messages received
- "Not registered" errors
- QR code generation fails

**Solutions:**

1. Generate new linking QR code:
   - Go to http://localhost:8084/setup
   - Click "Link Device"
   - Scan QR code with Signal app

2. Manual linking via CLI:
```bash
signal-cli link -n "Signal Bot"
# Outputs QR code in terminal
```

3. Verify registration:
```bash
signal-cli -u +YOUR_PHONE receive
```

---

#### Message Polling Not Working

**Symptoms:**
- Bot online but not receiving messages
- No reactions being sent
- Messages not appearing in web interface

**Solutions:**

1. Check Signal service status:
```bash
tail -f signal_service.log
```

2. Test manual receive:
```bash
signal-cli -u +YOUR_PHONE receive --json
```

3. Restart polling service:
```bash
./run_signal_service.sh --force
```

4. Check group monitoring:
   - Go to http://localhost:8084/groups
   - Ensure groups are marked as "Monitored"

---

### Database Issues

#### Duplicate Users

**Symptoms:**
- Same phone number appears multiple times
- Different UUIDs for same user
- Sync creates duplicates

**Solutions:**

1. Clear and resync users:
```bash
sqlite3 signal_bot.db "DELETE FROM users;"
# Then sync via web interface
```

2. Run deduplication:
```bash
sqlite3 signal_bot.db "
DELETE FROM users
WHERE rowid NOT IN (
  SELECT MIN(rowid)
  FROM users
  GROUP BY phone
);"
```

---

#### Database Locked

**Error:**
```
sqlite3.OperationalError: database is locked
```

**Solutions:**

1. Stop all services:
```bash
./manage.sh stop
```

2. Check for stuck processes:
```bash
fuser signal_bot.db
```

3. Backup and recreate:
```bash
cp signal_bot.db signal_bot.db.backup
sqlite3 signal_bot.db "VACUUM;"
```

---

#### Database Corruption

**Symptoms:**
- Random crashes
- Data inconsistencies
- SQL errors

**Solutions:**

1. Check integrity:
```bash
sqlite3 signal_bot.db "PRAGMA integrity_check;"
```

2. Recover data:
```bash
sqlite3 signal_bot.db ".dump" > backup.sql
rm signal_bot.db
sqlite3 signal_bot.db < backup.sql
```

3. Optimize database:
```bash
./cleanup_backups.sh
```

---

### Group Sync Issues

#### Groups Not Syncing

**Symptoms:**
- Groups page empty
- Sync hangs or times out
- "NoneType" errors

**Solutions:**

1. Check debug logs:
```bash
./run_signal_service.sh --debug
```

2. Manual group list:
```bash
signal-cli -u +YOUR_PHONE listGroups -d
```

3. Force refresh:
   - Go to http://localhost:8084/groups
   - Click "Sync Groups"
   - Wait for completion

---

#### Group Members Missing

**Symptoms:**
- Member count shows 0
- User filters empty
- Group statistics incorrect

**Solutions:**

1. Resync with members:
```bash
python3 -c "
from models.database import DatabaseManager
from services.setup import SetupService
db = DatabaseManager()
setup = SetupService(db)
setup.sync_groups_with_members()
"
```

---

### AI Feature Issues

#### Ollama Not Connecting

**Error:**
```
Connection refused to http://localhost:11434/
```

**Solutions:**

1. Check Ollama service:
```bash
systemctl status ollama
ollama list
```

2. Test connection:
```bash
curl http://localhost:11434/api/tags
```

3. Update configuration:
   - Go to http://localhost:8084/ai-config
   - Set correct Ollama host
   - Test connection

---

#### Model Loading Issues

**Symptoms:**
- "llm server loading model" errors
- Slow AI responses
- Timeouts

**Solutions:**

1. Preload model:
   - Go to http://localhost:8084/ai-config
   - Click "Preload Model"

2. Check available memory:
```bash
free -h
nvidia-smi  # If using GPU
```

3. Use smaller model:
```bash
ollama pull llama3.2:1b
# Update model in AI config
```

---

#### Sentiment Analysis Fails

**Symptoms:**
- Analysis returns empty
- "No messages found" error
- Incorrect results

**Solutions:**

1. Check message availability:
```bash
sqlite3 signal_bot.db "
SELECT COUNT(*) FROM messages
WHERE group_id = 'GROUP_ID'
AND DATE(timestamp) = '2025-09-18';"
```

2. Clear cache:
```bash
sqlite3 signal_bot.db "DELETE FROM sentiment_analysis;"
```

3. Enable debug logging:
```bash
LOG_LEVEL=DEBUG ./run_web_server.sh
```

---

### Performance Issues

#### High CPU Usage

**Symptoms:**
- System sluggish
- Fan running constantly
- Processes using 100% CPU

**Solutions:**

1. Check process usage:
```bash
top -p $(pgrep -f signal_bot -d,)
```

2. Increase polling interval:
```env
MESSAGE_POLLING_INTERVAL=60
```

3. Disable unused features:
```env
ENABLE_SENTIMENT_ANALYSIS=False
ENABLE_SUMMARIZATION=False
```

---

#### Memory Leaks

**Symptoms:**
- Memory usage growing over time
- Out of memory errors
- System swapping

**Solutions:**

1. Monitor memory:
```bash
watch -n 5 'ps aux | grep -E "(signal_service|web_server)"'
```

2. Restart services periodically:
```bash
# Add to crontab
0 4 * * * /path/to/signal-bot/restart.sh
```

3. Limit cache size:
```env
CACHE_TTL=300
BATCH_SIZE=50
```

---

#### Slow Web Interface

**Symptoms:**
- Pages load slowly
- Timeouts on API calls
- Database queries slow

**Solutions:**

1. Optimize database:
```bash
sqlite3 signal_bot.db "
VACUUM;
ANALYZE;
REINDEX;"
```

2. Clean old messages:
```bash
./cleanup_backups.sh
```

3. Add database indexes:
```bash
sqlite3 signal_bot.db "
CREATE INDEX IF NOT EXISTS idx_messages_timestamp
ON messages(timestamp);
CREATE INDEX IF NOT EXISTS idx_messages_group
ON messages(group_id);"
```

---

## Log Analysis

### Understanding Log Levels

- **DEBUG**: Detailed information for troubleshooting
- **INFO**: Normal operation messages
- **WARNING**: Something unexpected but handled
- **ERROR**: Serious problem that needs attention

### Key Log Patterns

#### Successful startup:
```
Signal polling service initialized
Bot instance lock acquired
Starting Signal CLI polling service
Signal polling service ready
```

#### Message processing:
```
Polling for new messages...
Processing N messages
Message from USER in GROUP
Sent reaction EMOJI to message
```

#### Sync operations:
```
Getting contacts from Signal CLI...
Found N contacts from Signal CLI
Synced N users to database
```

### Debug Mode

Enable detailed logging:

```bash
# For all services
export LOG_LEVEL=DEBUG
./restart.sh

# For specific service
./run_signal_service.sh --debug
```

## Health Checks

### Daily Maintenance

```bash
#!/bin/bash
# health_check.sh

echo "=== Signal Bot Health Check ==="

# 1. Check services
./check_status.sh

# 2. Database size
du -h signal_bot.db

# 3. Log rotation
./cleanup_backups.sh --dry-run

# 4. Test API
curl -s http://localhost:8084/api/status | jq .

# 5. Memory usage
ps aux | grep -E "(signal|web)" | awk '{sum+=$6} END {print "Total RSS: " sum/1024 " MB"}'
```

### Monitoring Script

```bash
#!/bin/bash
# monitor.sh

while true; do
    clear
    echo "=== Signal Bot Monitor ==="
    echo "Time: $(date)"
    echo

    # Process status
    ps aux | grep -E "(signal_service|web_server)" | grep -v grep

    # Port status
    netstat -tulpn 2>/dev/null | grep :8084

    # Recent logs
    echo -e "\n=== Recent Activity ==="
    tail -5 signal_service.log

    sleep 5
done
```

## Recovery Procedures

### Full Reset

```bash
# 1. Stop everything
./manage.sh stop

# 2. Backup data
cp signal_bot.db signal_bot.db.backup.$(date +%Y%m%d)
cp -r logs/ logs.backup.$(date +%Y%m%d)/

# 3. Clear logs
> signal_service.log
> web_server.log

# 4. Restart fresh
./manage.sh start
```

### Partial Recovery

```bash
# Just restart web server
pkill -f web_server.py
./run_web_server.sh

# Just restart Signal service
pkill -f signal_service.py
./run_signal_service.sh
```

## Getting Help

### Collect Debug Information

```bash
# Run diagnostic script
./manage.sh status > debug_info.txt
./manage.sh config >> debug_info.txt
./manage.sh test >> debug_info.txt
tail -100 signal_service.log >> debug_info.txt
tail -100 web_server.log >> debug_info.txt
```

### Check Documentation

- [README.md](../README.md) - Overview and quick start
- [CONFIGURATION.md](CONFIGURATION.md) - Configuration options
- [ARCHITECTURE.md](ARCHITECTURE.md) - System design
- [API.md](API.md) - API endpoints

### Report Issues

When reporting issues, include:

1. Output of `./manage.sh status`
2. Configuration (without API keys)
3. Relevant log excerpts
4. Steps to reproduce
5. Expected vs actual behavior

## Prevention Tips

1. **Regular Maintenance**
   - Run `./cleanup_backups.sh` weekly
   - Monitor log file sizes
   - Check database size

2. **Monitoring**
   - Set up log rotation
   - Monitor system resources
   - Check service health daily

3. **Backups**
   - Backup database regularly
   - Export configuration
   - Document customizations

4. **Updates**
   - Keep Signal CLI updated
   - Update Python dependencies
   - Review security updates