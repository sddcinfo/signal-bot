# Database Schema Optimization Report

## Current Schema Analysis

### 🔴 Critical Issues

#### 1. Redundant Tables
**processed_messages table is completely redundant**
- Contains 466 rows vs 808 messages
- Duplicates data already in messages table
- The `reacted` column in messages already tracks processing
- **Recommendation**: Remove processed_messages table entirely

#### 2. Unused User Columns
**7 name-related columns in users table, ALL with 0 values**
- contact_name (0/119 users)
- profile_name (0/119 users)
- username (0/119 users)
- given_name (0/119 users)
- family_name (0/119 users)
- profile_given_name (0/119 users)
- profile_family_name (0/119 users)
- **Recommendation**: Remove all these columns, keep only `friendly_name`

#### 3. Inconsistent Timestamp Types
- messages.timestamp: INTEGER (milliseconds)
- All other timestamps: DATETIME strings
- **Recommendation**: Standardize on INTEGER milliseconds for performance

### 🟡 Performance Issues

#### 1. Missing Critical Indexes
```sql
-- Missing indexes for common queries
CREATE INDEX idx_messages_sender ON messages(sender_uuid);
CREATE INDEX idx_messages_timestamp_desc ON messages(timestamp DESC);
CREATE INDEX idx_group_members_user ON group_members(user_uuid);
CREATE INDEX idx_messages_group_sender ON messages(group_id, sender_uuid);
CREATE INDEX idx_messages_group_timestamp ON messages(group_id, timestamp DESC);
```

#### 2. Inefficient Storage
- attachments.file_data BLOB: Storing binary in DB bloats size
- **Recommendation**: Keep only file_path, store files on disk

#### 3. No Archiving Strategy
- 808 messages growing unbounded
- No partitioning or archival process
- **Recommendation**: Archive messages older than 30-90 days

### 🟢 Good Practices Found
- Proper foreign key constraints
- Primary keys on all tables
- Some useful indexes already present

## Proposed Optimized Schema

### Phase 1: Quick Wins (Safe, Immediate)

```sql
-- 1. Drop unused columns from users table
ALTER TABLE users DROP COLUMN contact_name;
ALTER TABLE users DROP COLUMN profile_name;
ALTER TABLE users DROP COLUMN username;
ALTER TABLE users DROP COLUMN given_name;
ALTER TABLE users DROP COLUMN family_name;
ALTER TABLE users DROP COLUMN profile_given_name;
ALTER TABLE users DROP COLUMN profile_family_name;

-- 2. Add missing performance indexes
CREATE INDEX idx_messages_sender ON messages(sender_uuid);
CREATE INDEX idx_messages_timestamp_desc ON messages(timestamp DESC);
CREATE INDEX idx_group_members_user ON group_members(user_uuid);
CREATE INDEX idx_messages_group_sender ON messages(group_id, sender_uuid);
CREATE INDEX idx_messages_group_timestamp ON messages(group_id, timestamp DESC);

-- 3. Clean up bot_status table (keep only last 100 entries)
DELETE FROM bot_status
WHERE id NOT IN (
    SELECT id FROM bot_status
    ORDER BY created_at DESC
    LIMIT 100
);
```

### Phase 2: Structural Improvements (Requires Migration)

```sql
-- New optimized messages table
CREATE TABLE messages_new (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp INTEGER NOT NULL,
    group_id TEXT NOT NULL REFERENCES groups(group_id),
    sender_uuid TEXT NOT NULL REFERENCES users(uuid),
    message_text TEXT,
    reacted BOOLEAN DEFAULT FALSE,
    created_at INTEGER NOT NULL DEFAULT (strftime('%s', 'now') * 1000)
);

-- Migrate data
INSERT INTO messages_new (id, timestamp, group_id, sender_uuid, message_text, reacted)
SELECT id, timestamp, group_id, sender_uuid, message_text, reacted FROM messages;

-- Swap tables
DROP TABLE messages;
ALTER TABLE messages_new RENAME TO messages;

-- Drop redundant processed_messages table
DROP TABLE processed_messages;
```

### Phase 3: Archive Strategy

```sql
-- Create archive table for old messages
CREATE TABLE messages_archive (
    id INTEGER PRIMARY KEY,
    timestamp INTEGER NOT NULL,
    group_id TEXT,
    sender_uuid TEXT,
    message_text TEXT,
    archived_at INTEGER DEFAULT (strftime('%s', 'now') * 1000)
);

-- Archive messages older than 90 days
INSERT INTO messages_archive (id, timestamp, group_id, sender_uuid, message_text)
SELECT id, timestamp, group_id, sender_uuid, message_text
FROM messages
WHERE timestamp < (strftime('%s', 'now') * 1000 - 90*24*60*60*1000);

DELETE FROM messages
WHERE timestamp < (strftime('%s', 'now') * 1000 - 90*24*60*60*1000);
```

## Performance Impact

### Before Optimization
- Database size: 5.2 MB
- 16 columns in users table (7 always NULL)
- Redundant processed_messages table
- Missing critical indexes
- No archival strategy

### After Optimization
- **Expected size reduction**: ~20-30%
- **Query performance gain**: 2-5x for common queries
- **Cleaner schema**: 9 vs 16 columns in users
- **Removed redundancy**: No processed_messages table
- **Better scalability**: Archive strategy for old data

## Implementation Priority

### Immediate (No Risk)
1. ✅ Add missing indexes
2. ✅ Clean bot_status table
3. ✅ Document schema

### Short Term (Low Risk)
1. Remove unused user columns
2. Drop processed_messages table
3. Update code to not reference removed items

### Long Term (Planned)
1. Implement message archival
2. Convert timestamps to consistent INTEGER
3. Move attachment data to filesystem

## Code Changes Required

### Files to Update After Schema Changes:
1. `models/database.py`: Remove references to dropped columns
2. `services/messaging.py`: Remove processed_messages usage
3. `web/pages/*.py`: Update any queries using removed columns

## Testing Plan

1. **Backup database** ✅ (already done)
2. **Test in dev environment** first
3. **Run optimization phases** incrementally
4. **Validate functionality** after each phase
5. **Monitor performance** improvements

## Recommended Action

Start with Phase 1 (Quick Wins) immediately:
```bash
# Add indexes (safe, reversible)
sqlite3 signal_bot.db < phase1_indexes.sql

# Test everything still works
./run_tests.sh

# If successful, proceed to Phase 2
```

This optimization will make the database:
- **Faster**: Better indexes, less data to scan
- **Smaller**: Remove redundant data
- **Cleaner**: Simpler schema, easier to maintain
- **More scalable**: Archive strategy for growth