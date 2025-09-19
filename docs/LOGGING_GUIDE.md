# Signal Bot Logging Guidelines

## Overview
The Signal Bot uses a three-tier logging system: INFO, WARNING, and DEBUG.
- **INFO & WARNING** are shown by default
- **DEBUG** is only shown when started with the `--debug` flag

## Starting Services with Debug Mode

```bash
# Start with debug logging
./manage.sh start --daemon --debug

# Restart with debug logging
./manage.sh restart --daemon --debug

# Start without debug (default - INFO/WARNING only)
./manage.sh start --daemon
```

## Log Levels and When to Use Them

### DEBUG Level (Hidden by default, shown with --debug)
Use for detailed diagnostic information that's only useful when troubleshooting:
```python
logger.debug("Envelope processing details: %s", envelope_id)
logger.debug("Database query: %s", query)
logger.debug("Socket connection details: %s", socket_info)
logger.debug("Skipping non-relevant envelope type: %s", envelope_type)
logger.debug("Reaction selection logic: considering %s", emoji_list)
```

### INFO Level (Always shown)
Use for normal operational messages that confirm things are working:
```python
logger.info("Service started successfully")
logger.info("Message received from %s", user_id)
logger.info("Reaction sent to message #%d", message_id)
logger.info("Database connection established")
logger.info("Web server listening on port %d", port)
```

### WARNING Level (Always shown)
Use for unexpected situations that don't stop operation:
```python
logger.warning("Configuration not found, using defaults")
logger.warning("Failed to send reaction, will retry")
logger.warning("Database locked, waiting...")
logger.warning("Rate limit approaching: %d/%d", current, max)
```

### ERROR Level (Always shown)
Use for serious problems that likely cause failures:
```python
logger.error("Failed to connect to signal-cli: %s", error)
logger.error("Database connection failed: %s", error)
logger.error("Critical configuration missing: %s", param)
logger.error("Unhandled exception in message processor", exc_info=True)
```

## Best Practices

### 1. Use Appropriate Level for Context
```python
# Bad - using INFO for debugging details
logger.info("Checking if envelope has dataMessage field")

# Good - using DEBUG for implementation details
logger.debug("Checking if envelope has dataMessage field")
```

### 2. Include Relevant Context
```python
# Bad - no context
logger.error("Failed to process")

# Good - includes context
logger.error("Failed to process message %s from user %s: %s", msg_id, user_id, error)
```

### 3. Use Structured Logging for Complex Data
```python
# For complex objects, use DEBUG level
logger.debug("Envelope details: %s", json.dumps(envelope, indent=2))

# For summaries, use INFO level
logger.info("Processed message #%d from %s", msg_num, user_id[:8])
```

### 4. Avoid Logging Sensitive Information
```python
# Bad - logs full phone number
logger.info("User phone: %s", phone_number)

# Good - logs partial identifier
logger.info("User: %s", phone_number[:4] + "****" if phone_number else "unknown")
```

### 5. Use Consistent Message Format
```python
# Service startup
logger.info("Starting %s service on port %d", service_name, port)

# Success messages
logger.info("✅ Successfully processed %d messages", count)

# Failure messages
logger.warning("❌ Failed to process message #%d", msg_id)
```

## Common Patterns

### Service Lifecycle
```python
# Startup
logger.info("Initializing %s service", service_name)
logger.debug("Configuration: %s", config_details)
logger.info("Service started successfully")

# Shutdown
logger.info("Shutting down %s service", service_name)
logger.debug("Cleanup details: %s", cleanup_info)
logger.info("Service stopped")
```

### Message Processing
```python
# Reception
logger.info("📨 Message received from %s", sender[:8])
logger.debug("Message details: timestamp=%s, group=%s", timestamp, group_id)

# Processing
logger.debug("Processing message through pipeline")
logger.info("✅ Message processed successfully")

# Errors
logger.warning("⚠️  Message processing delayed: %s", reason)
logger.error("❌ Message processing failed: %s", error)
```

### Database Operations
```python
# Connections
logger.info("Connecting to database: %s", db_path)
logger.debug("Connection parameters: %s", params)

# Queries
logger.debug("Executing query: %s", query[:100])
logger.info("Query completed: %d rows affected", row_count)

# Errors
logger.warning("Database locked, retrying in %ds", retry_delay)
logger.error("Database query failed: %s", error)
```

## Viewing Logs

### Live Monitoring
```bash
# View all logs (INFO and above)
tail -f signal_daemon.log

# View only warnings and errors
tail -f signal_daemon.log | grep -E "(WARNING|ERROR)"

# View without debug messages
tail -f signal_daemon.log | grep -v DEBUG
```

### Log Analysis
```bash
# Count log levels
grep -oE "(DEBUG|INFO|WARNING|ERROR)" signal_daemon.log | sort | uniq -c

# Find all errors
grep ERROR signal_daemon.log

# Find specific component logs
grep "\[DaemonListener\]" signal_daemon.log
```

## Environment Variables

You can also control logging via environment variables:
```bash
# Set log level for all services
export LOG_LEVEL=DEBUG
./manage.sh start --daemon

# Or for specific service
LOG_LEVEL=DEBUG python3 signal_daemon_service.py
```

## Summary

- Use **DEBUG** for detailed diagnostic information
- Use **INFO** for normal operational messages
- Use **WARNING** for recoverable issues
- Use **ERROR** for serious problems
- Start with `--debug` flag to see DEBUG messages
- Keep production logs clean by using appropriate levels