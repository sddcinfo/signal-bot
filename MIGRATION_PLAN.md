# Signal Bot Database Migration Plan

## Current Status
- **Database Size**: 5.2 MB
- **Total Messages**: 797
- **Total Users**: 119 (2 configured with reactions)
- **Total Groups**: 35 (3 monitored)
- **Backups Created**:
  - Full: `/home/sysadmin/claude/signal-bot/backups/db/full_backup_20250919_061422.db.gz`
  - Critical: `/home/sysadmin/claude/signal-bot/backups/db/critical_backup_20250919_061422.sql.gz`

## Migration Process Overview

### Phase 1: Preparation & Backup ✅ COMPLETED
1. Create full database backup (compressed)
2. Create critical data backup (messages, attachments, processed_messages)
3. Document current configuration

### Phase 2: Fresh Database & Linking
1. Move current database to `.old` suffix
2. Initialize fresh database with schema
3. Re-link Signal device using signal-cli
4. Run clean import to sync contacts and groups

### Phase 3: Selective Data Restoration
Import from backup:
- All messages and attachments
- User reaction configurations (3 users)
- Group monitoring settings (3 groups)
- Bot configuration (excluding setup-related keys)

## What "Clean Import" Actually Does
Based on code analysis and UI confirmation message:
1. **Clears**: All users and group memberships from database
2. **Imports**: Fresh contact and group data from signal-cli
3. **Preserves**: User reactions and monitored group settings
4. **Does NOT touch**: Messages, attachments, or other historical data

This is actually safer than full migration as it preserves configurations!

## Critical Risks & Mitigations

### 🔴 HIGH RISK: UUID/ID Changes
**Risk**: When re-linking device, user UUIDs and group IDs may change
**Impact**:
- Messages won't map to correct users
- Group monitoring settings won't apply
- User reaction configs become orphaned

**Mitigation**:
- Map old UUIDs to new ones using phone numbers as keys
- Map old group IDs to new ones using group names
- Create translation tables during import

### 🟡 MEDIUM RISK: Signal-CLI State Desync
**Risk**: signal-cli data directory may become inconsistent
**Impact**: Failed message sending/receiving

**Mitigation**:
- Backup signal-cli data directory before starting
- Consider full signal-cli reset if issues occur

### 🟡 MEDIUM RISK: Lost Attachment Files
**Risk**: Attachment file paths may not resolve
**Impact**: Historical attachments unavailable

**Mitigation**:
- Verify attachment files exist in filesystem
- Update paths in database if needed

### 🟢 LOW RISK: Temporary Service Downtime
**Risk**: Bot will be offline during migration
**Impact**: Missed messages during migration window

**Mitigation**:
- Perform during low-activity period
- Complete migration quickly (<30 minutes)

## Data Mapping Strategy

### User Mapping
```sql
-- Create mapping table
CREATE TEMP TABLE user_mapping AS
SELECT old.uuid as old_uuid, new.uuid as new_uuid, old.phone_number
FROM backup.users old
JOIN users new ON old.phone_number = new.phone_number;

-- Update messages
UPDATE messages
SET sender_uuid = (SELECT new_uuid FROM user_mapping WHERE old_uuid = messages.sender_uuid);
```

### Group Mapping
```sql
-- Create mapping based on group names (risky if names changed)
CREATE TEMP TABLE group_mapping AS
SELECT old.group_id as old_id, new.group_id as new_id
FROM backup.groups old
JOIN groups new ON old.group_name = new.group_name;
```

## Rollback Plan
1. Stop bot service
2. Restore original database from backup
3. Restore signal-cli data directory if backed up
4. Restart bot service

## Recommended Approach

### Option A: Conservative (Recommended)
1. Create test environment with copy of data
2. Test full migration process
3. Document all UUID/ID mappings
4. Perform production migration with tested mappings

### Option B: Direct Migration (Risky)
1. Perform migration on production
2. Handle issues as they arise
3. Risk data loss or corruption

## Pre-Migration Checklist
- [ ] Full database backup created
- [ ] Signal-cli data directory backed up
- [ ] Bot service stopped
- [ ] All active users notified of maintenance
- [ ] UUID mapping strategy tested
- [ ] Rollback procedure documented

## Post-Migration Validation
- [ ] All groups visible in web interface
- [ ] Monitored groups correctly marked
- [ ] User reactions working
- [ ] Historical messages accessible
- [ ] Bot can send/receive messages
- [ ] Attachments loading correctly

## Commands for Migration

```bash
# 1. Stop bot
./stop_bot.sh

# 2. Backup current state
cp signal_bot.db signal_bot.db.pre_migration
cp -r ~/.local/share/signal-cli ~/.local/share/signal-cli.backup

# 3. Create fresh database
mv signal_bot.db signal_bot.db.old
python3 -c "from models.database import DatabaseManager; DatabaseManager()"

# 4. Re-link device (WILL NEED QR CODE)
signal-cli link -n "Signal Bot"

# 5. Run clean import
python3 -c "from services.setup import SetupService; s = SetupService(); s.clean_import()"

# 6. Import historical data (custom script needed)
python3 migrate_historical_data.py

# 7. Start bot
./start_bot.sh
```

## Decision Required

**Should we proceed with this migration?**

The main benefit would be a clean, fresh signal-cli state. However, the risks around UUID/ID changes are significant and could result in:
- Lost message history associations
- Broken user configurations
- Incorrect group monitoring

**Alternative Approach**: Instead of full migration, we could:
1. Keep current database
2. Run periodic cleanup scripts
3. Archive old messages beyond 30 days
4. Optimize indexes for better performance

This would be much safer and achieve similar results without the risks.