#!/usr/bin/env python3
"""
Signal Bot Database Backup and Management System

Handles database backups with focus on critical data (messages/attachments)
and provides intelligent size management while keeping everything in the DB.
"""

import os
import sys
import sqlite3
import gzip
import shutil
import json
import hashlib
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import argparse
import zlib

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config.settings import Config
from utils.common import format_file_size


class DatabaseManager:
    """Advanced database backup and management system."""

    def __init__(self):
        self.config = Config()
        self.db_path = Path(self.config.DATABASE_PATH)
        self.backup_dir = Path("backups/db")
        self.backup_dir.mkdir(parents=True, exist_ok=True)

    # ========== Backup Strategies ==========

    def backup_full(self, compress: bool = True) -> Path:
        """
        Create a full database backup.

        Args:
            compress: Whether to compress the backup

        Returns:
            Path to backup file
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"full_backup_{timestamp}.db"

        if compress:
            backup_name += ".gz"

        backup_path = self.backup_dir / backup_name

        print(f"Creating full backup: {backup_path}")

        # Use SQLite backup API for consistency
        source = sqlite3.connect(self.db_path)

        if compress:
            # Backup to temp file first, then compress
            temp_path = self.backup_dir / f"temp_{timestamp}.db"
            dest = sqlite3.connect(temp_path)
            source.backup(dest)
            dest.close()

            # Compress
            with open(temp_path, 'rb') as f_in:
                with gzip.open(backup_path, 'wb', compresslevel=9) as f_out:
                    shutil.copyfileobj(f_in, f_out)

            # Remove temp file
            temp_path.unlink()

        else:
            dest = sqlite3.connect(backup_path)
            source.backup(dest)
            dest.close()

        source.close()

        size = backup_path.stat().st_size
        print(f"✅ Full backup created: {format_file_size(size)}")

        return backup_path

    def backup_critical(self) -> Path:
        """
        Backup only critical data (messages, attachments, processed_messages).
        This is much smaller than full backup as it excludes derived data.

        Returns:
            Path to backup file
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = self.backup_dir / f"critical_backup_{timestamp}.sql.gz"

        print(f"Creating critical data backup: {backup_path}")

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Tables to backup (in dependency order)
        critical_tables = [
            'messages',
            'attachments',
            'processed_messages'
        ]

        sql_dump = []

        # Add header
        sql_dump.append("-- Signal Bot Critical Data Backup")
        sql_dump.append(f"-- Created: {datetime.now()}")
        sql_dump.append("-- This backup contains only critical, non-recoverable data")
        sql_dump.append("BEGIN TRANSACTION;")
        sql_dump.append("")

        for table in critical_tables:
            # Get table schema
            cursor.execute(f"SELECT sql FROM sqlite_master WHERE type='table' AND name=?", (table,))
            schema = cursor.fetchone()
            if schema:
                sql_dump.append(f"-- Table: {table}")
                sql_dump.append(f"DROP TABLE IF EXISTS {table};")
                sql_dump.append(schema[0] + ";")
                sql_dump.append("")

                # Get data
                cursor.execute(f"SELECT * FROM {table}")
                rows = cursor.fetchall()

                if rows:
                    # Get column names
                    cursor.execute(f"PRAGMA table_info({table})")
                    columns = [col[1] for col in cursor.fetchall()]

                    # Add insert statements
                    for row in rows:
                        values = []
                        for val in row:
                            if val is None:
                                values.append("NULL")
                            elif isinstance(val, (int, float)):
                                values.append(str(val))
                            elif isinstance(val, bytes):
                                # For binary data (attachments), use hex encoding
                                values.append(f"X'{val.hex()}'")
                            else:
                                # Escape single quotes in strings
                                escaped = str(val).replace("'", "''")
                                values.append(f"'{escaped}'")

                        sql_dump.append(f"INSERT INTO {table} ({','.join(columns)}) VALUES ({','.join(values)});")

                sql_dump.append("")

        sql_dump.append("COMMIT;")

        # Write compressed backup
        with gzip.open(backup_path, 'wt', encoding='utf-8', compresslevel=9) as f:
            f.write('\n'.join(sql_dump))

        conn.close()

        size = backup_path.stat().st_size
        print(f"✅ Critical backup created: {format_file_size(size)}")

        return backup_path

    def backup_incremental(self, since_hours: int = 24) -> Optional[Path]:
        """
        Backup only recent messages and attachments.

        Args:
            since_hours: Backup messages from last N hours

        Returns:
            Path to backup file or None if no new data
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = self.backup_dir / f"incremental_{timestamp}_{since_hours}h.sql.gz"

        cutoff_time = datetime.now() - timedelta(hours=since_hours)

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Count recent messages
        cursor.execute("SELECT COUNT(*) FROM messages WHERE timestamp > ?", (cutoff_time,))
        message_count = cursor.fetchone()[0]

        if message_count == 0:
            print(f"No new messages in the last {since_hours} hours")
            conn.close()
            return None

        print(f"Backing up {message_count} messages from last {since_hours} hours")

        sql_dump = []
        sql_dump.append(f"-- Incremental Backup: Last {since_hours} hours")
        sql_dump.append(f"-- Created: {datetime.now()}")
        sql_dump.append(f"-- Messages: {message_count}")
        sql_dump.append("BEGIN TRANSACTION;")
        sql_dump.append("")

        # Get recent messages
        cursor.execute("SELECT * FROM messages WHERE timestamp > ?", (cutoff_time,))
        messages = cursor.fetchall()

        # Get message IDs for attachment lookup
        message_ids = [msg[0] for msg in messages]

        # Add messages
        if messages:
            cursor.execute("PRAGMA table_info(messages)")
            columns = [col[1] for col in cursor.fetchall()]

            for msg in messages:
                values = []
                for val in msg:
                    if val is None:
                        values.append("NULL")
                    elif isinstance(val, (int, float)):
                        values.append(str(val))
                    else:
                        escaped = str(val).replace("'", "''")
                        values.append(f"'{escaped}'")

                sql_dump.append(f"INSERT OR IGNORE INTO messages ({','.join(columns)}) VALUES ({','.join(values)});")

        # Get attachments for these messages
        if message_ids:
            placeholders = ','.join('?' * len(message_ids))
            cursor.execute(f"SELECT * FROM attachments WHERE message_id IN ({placeholders})", message_ids)
            attachments = cursor.fetchall()

            if attachments:
                cursor.execute("PRAGMA table_info(attachments)")
                columns = [col[1] for col in cursor.fetchall()]

                for att in attachments:
                    values = []
                    for val in att:
                        if val is None:
                            values.append("NULL")
                        elif isinstance(val, (int, float)):
                            values.append(str(val))
                        elif isinstance(val, bytes):
                            values.append(f"X'{val.hex()}'")
                        else:
                            escaped = str(val).replace("'", "''")
                        values.append(f"'{escaped}'")

                    sql_dump.append(f"INSERT OR IGNORE INTO attachments ({','.join(columns)}) VALUES ({','.join(values)});")

        sql_dump.append("")
        sql_dump.append("COMMIT;")

        # Write compressed backup
        with gzip.open(backup_path, 'wt', encoding='utf-8', compresslevel=9) as f:
            f.write('\n'.join(sql_dump))

        conn.close()

        size = backup_path.stat().st_size
        print(f"✅ Incremental backup created: {format_file_size(size)}")

        return backup_path

    # ========== Size Management ==========

    def analyze_database(self) -> Dict:
        """Analyze database size and content."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        analysis = {
            'total_size': self.db_path.stat().st_size,
            'tables': {},
            'recommendations': []
        }

        # Analyze each table (using pragma instead of dbstat for accuracy)
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()

        for table_name in tables:
            # Count rows and estimate size
            cursor.execute(f"SELECT COUNT(*) FROM {table_name[0]}")
            row_count = cursor.fetchone()[0]

            # For attachments, get actual data size
            if table_name[0] == 'attachments':
                cursor.execute("SELECT SUM(LENGTH(file_data)) FROM attachments")
                data_size = cursor.fetchone()[0] or 0
                analysis['tables'][table_name[0]] = {
                    'size': data_size,
                    'size_formatted': format_file_size(data_size),
                    'rows': row_count
                }
            else:
                # Rough estimate for other tables (1KB per row average)
                estimated_size = row_count * 1024
                analysis['tables'][table_name[0]] = {
                    'size': estimated_size,
                    'size_formatted': format_file_size(estimated_size),
                    'rows': row_count
                }

        # Analyze attachments
        cursor.execute("""
            SELECT
                COUNT(*) as count,
                AVG(LENGTH(file_data)) as avg_size,
                MAX(LENGTH(file_data)) as max_size,
                SUM(LENGTH(file_data)) as total_size
            FROM attachments
        """)
        att_stats = cursor.fetchone()

        analysis['attachments'] = {
            'count': att_stats[0],
            'avg_size': att_stats[1] or 0,
            'max_size': att_stats[2] or 0,
            'total_size': att_stats[3] or 0
        }

        # Check for optimization opportunities
        cursor.execute("PRAGMA page_count")
        page_count = cursor.fetchone()[0]
        cursor.execute("PRAGMA freelist_count")
        free_pages = cursor.fetchone()[0]

        analysis['fragmentation'] = {
            'total_pages': page_count,
            'free_pages': free_pages,
            'fragmentation_percent': (free_pages / page_count * 100) if page_count > 0 else 0
        }

        # Recommendations
        if analysis['fragmentation']['fragmentation_percent'] > 20:
            analysis['recommendations'].append(f"High fragmentation ({analysis['fragmentation']['fragmentation_percent']:.1f}%). Run VACUUM to reclaim space.")

        # Check for old messages
        cursor.execute("SELECT COUNT(*) FROM messages WHERE timestamp < datetime('now', '-90 days')")
        old_messages = cursor.fetchone()[0]
        if old_messages > 100:
            analysis['recommendations'].append(f"Found {old_messages} messages older than 90 days. Consider archiving.")

        conn.close()
        return analysis

    def compress_attachments(self, older_than_days: int = 30) -> int:
        """
        Compress attachments older than specified days IN PLACE.
        This reduces DB size while keeping data in the database.

        Args:
            older_than_days: Compress attachments older than this

        Returns:
            Number of attachments compressed
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cutoff_date = datetime.now() - timedelta(days=older_than_days)

        # Find uncompressed attachments
        cursor.execute("""
            SELECT a.id, a.file_data, LENGTH(a.file_data) as size
            FROM attachments a
            JOIN messages m ON a.message_id = m.id
            WHERE m.timestamp < ?
            AND a.file_data NOT LIKE 'COMPRESSED:%'
        """, (cutoff_date,))

        attachments = cursor.fetchall()
        compressed_count = 0
        space_saved = 0

        for att_id, file_data, original_size in attachments:
            if file_data:
                # Compress with zlib (max compression)
                compressed = zlib.compress(file_data, level=9)

                # Only update if compression actually saves space
                if len(compressed) < original_size * 0.9:  # At least 10% savings
                    # Mark as compressed with a prefix
                    compressed_with_marker = b'COMPRESSED:' + compressed

                    cursor.execute("""
                        UPDATE attachments
                        SET file_data = ?
                        WHERE id = ?
                    """, (compressed_with_marker, att_id))

                    space_saved += original_size - len(compressed_with_marker)
                    compressed_count += 1

                    print(f"  Compressed attachment {att_id}: {format_file_size(original_size)} → {format_file_size(len(compressed_with_marker))}")

        conn.commit()
        conn.close()

        if compressed_count > 0:
            print(f"✅ Compressed {compressed_count} attachments, saved {format_file_size(space_saved)}")
        else:
            print("No attachments needed compression")

        return compressed_count

    def vacuum_database(self) -> Dict:
        """
        Vacuum the database to reclaim space and defragment.

        Returns:
            Statistics about the operation
        """
        print("Vacuuming database...")

        size_before = self.db_path.stat().st_size

        conn = sqlite3.connect(self.db_path)
        conn.execute("VACUUM")
        conn.close()

        size_after = self.db_path.stat().st_size

        stats = {
            'size_before': size_before,
            'size_after': size_after,
            'space_reclaimed': size_before - size_after,
            'reduction_percent': ((size_before - size_after) / size_before * 100) if size_before > 0 else 0
        }

        print(f"✅ Database vacuumed: {format_file_size(size_before)} → {format_file_size(size_after)}")
        print(f"   Space reclaimed: {format_file_size(stats['space_reclaimed'])} ({stats['reduction_percent']:.1f}%)")

        return stats

    def archive_old_data(self, older_than_days: int = 180) -> Optional[Path]:
        """
        Move old messages to an archive database.

        Args:
            older_than_days: Archive messages older than this

        Returns:
            Path to archive file or None if no data to archive
        """
        cutoff_date = datetime.now() - timedelta(days=older_than_days)

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Count old messages
        cursor.execute("SELECT COUNT(*) FROM messages WHERE timestamp < ?", (cutoff_date,))
        old_count = cursor.fetchone()[0]

        if old_count == 0:
            print(f"No messages older than {older_than_days} days to archive")
            conn.close()
            return None

        print(f"Archiving {old_count} messages older than {older_than_days} days")

        # Create archive database
        timestamp = datetime.now().strftime("%Y%m%d")
        archive_path = self.backup_dir / f"archive_{timestamp}_{older_than_days}d.db"

        archive_conn = sqlite3.connect(archive_path)

        # Copy old data to archive
        conn.execute(f"ATTACH DATABASE '{archive_path}' AS archive")

        # Create tables in archive
        for table in ['messages', 'attachments', 'processed_messages']:
            cursor.execute(f"SELECT sql FROM sqlite_master WHERE type='table' AND name='{table}'")
            schema = cursor.fetchone()
            if schema:
                conn.execute(f"CREATE TABLE IF NOT EXISTS archive.{table} AS SELECT * FROM {table} WHERE 1=0")

        # Copy old messages
        conn.execute("""
            INSERT INTO archive.messages
            SELECT * FROM messages
            WHERE timestamp < ?
        """, (cutoff_date,))

        # Copy related attachments
        conn.execute("""
            INSERT INTO archive.attachments
            SELECT a.* FROM attachments a
            JOIN messages m ON a.message_id = m.id
            WHERE m.timestamp < ?
        """, (cutoff_date,))

        # Copy related processed_messages
        conn.execute("""
            INSERT INTO archive.processed_messages
            SELECT p.* FROM processed_messages p
            JOIN messages m ON p.message_id = m.message_id
            WHERE m.timestamp < ?
        """, (cutoff_date,))

        # Delete from main database (in reverse order due to foreign keys)
        conn.execute("""
            DELETE FROM attachments
            WHERE message_id IN (
                SELECT id FROM messages WHERE timestamp < ?
            )
        """, (cutoff_date,))

        conn.execute("DELETE FROM messages WHERE timestamp < ?", (cutoff_date,))

        conn.execute("DETACH DATABASE archive")
        conn.commit()

        # Compress archive
        archive_conn.execute("VACUUM")
        archive_conn.close()

        conn.close()

        # Compress archive file
        compressed_path = Path(str(archive_path) + '.gz')
        with open(archive_path, 'rb') as f_in:
            with gzip.open(compressed_path, 'wb', compresslevel=9) as f_out:
                shutil.copyfileobj(f_in, f_out)

        archive_path.unlink()

        size = compressed_path.stat().st_size
        print(f"✅ Archive created: {compressed_path.name} ({format_file_size(size)})")
        print(f"   Archived {old_count} messages")

        # Now vacuum main database to reclaim space
        self.vacuum_database()

        return compressed_path

    # ========== Backup Management ==========

    def list_backups(self) -> List[Dict]:
        """List all available backups."""
        backups = []

        # Collect all backup files
        all_backups = list(self.backup_dir.glob("*backup*.*")) + list(self.backup_dir.glob("*archive*.*"))

        for backup_file in sorted(all_backups, key=lambda x: x.stat().st_mtime, reverse=True):
            info = {
                'name': backup_file.name,
                'path': backup_file,
                'size': backup_file.stat().st_size,
                'size_formatted': format_file_size(backup_file.stat().st_size),
                'created': datetime.fromtimestamp(backup_file.stat().st_mtime),
                'type': 'unknown'
            }

            # Determine backup type
            if 'full_backup' in backup_file.name:
                info['type'] = 'full'
            elif 'critical_backup' in backup_file.name:
                info['type'] = 'critical'
            elif 'incremental' in backup_file.name:
                info['type'] = 'incremental'
            elif 'archive' in backup_file.name:
                info['type'] = 'archive'

            backups.append(info)

        return backups

    def rotate_backups(self, keep_daily: int = 7, keep_weekly: int = 4, keep_monthly: int = 6) -> int:
        """
        Rotate backups according to retention policy.

        Args:
            keep_daily: Number of daily backups to keep
            keep_weekly: Number of weekly backups to keep
            keep_monthly: Number of monthly backups to keep

        Returns:
            Number of backups deleted
        """
        now = datetime.now()
        backups = self.list_backups()

        # Group backups by age
        daily = []
        weekly = []
        monthly = []
        to_delete = []

        for backup in backups:
            if backup['type'] == 'archive':
                continue  # Never auto-delete archives

            age_days = (now - backup['created']).days

            if age_days <= keep_daily:
                daily.append(backup)
            elif age_days <= keep_weekly * 7:
                # Keep one per week
                week_num = age_days // 7
                if not any(b for b in weekly if (now - b['created']).days // 7 == week_num):
                    weekly.append(backup)
                else:
                    to_delete.append(backup)
            elif age_days <= keep_monthly * 30:
                # Keep one per month
                month_num = age_days // 30
                if not any(b for b in monthly if (now - b['created']).days // 30 == month_num):
                    monthly.append(backup)
                else:
                    to_delete.append(backup)
            else:
                to_delete.append(backup)

        # Delete old backups
        deleted_count = 0
        for backup in to_delete:
            backup['path'].unlink()
            print(f"  Deleted old backup: {backup['name']}")
            deleted_count += 1

        if deleted_count > 0:
            print(f"✅ Deleted {deleted_count} old backups")

        return deleted_count

    def restore_backup(self, backup_path: Path, target_path: Optional[Path] = None) -> bool:
        """
        Restore a backup.

        Args:
            backup_path: Path to backup file
            target_path: Where to restore (default: main database)

        Returns:
            Success status
        """
        if not backup_path.exists():
            print(f"❌ Backup file not found: {backup_path}")
            return False

        if target_path is None:
            target_path = self.db_path

            # Safety: backup current database first
            emergency_backup = self.backup_dir / f"pre_restore_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
            shutil.copy2(self.db_path, emergency_backup)
            print(f"Created emergency backup: {emergency_backup.name}")

        print(f"Restoring from: {backup_path.name}")

        # Handle compressed backups
        if backup_path.suffix == '.gz':
            if '.sql' in backup_path.name:
                # SQL dump - need to execute
                with gzip.open(backup_path, 'rt', encoding='utf-8') as f:
                    sql = f.read()

                conn = sqlite3.connect(target_path)
                conn.executescript(sql)
                conn.close()
            else:
                # Compressed database file
                with gzip.open(backup_path, 'rb') as f_in:
                    with open(target_path, 'wb') as f_out:
                        shutil.copyfileobj(f_in, f_out)
        else:
            # Direct database file
            shutil.copy2(backup_path, target_path)

        print(f"✅ Backup restored successfully")
        return True


def main():
    """CLI interface for database management."""
    parser = argparse.ArgumentParser(
        description='Signal Bot Database Management',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    subparsers = parser.add_subparsers(dest='command', help='Commands')

    # Backup commands
    backup_parser = subparsers.add_parser('backup', help='Create backup')
    backup_parser.add_argument('type', choices=['full', 'critical', 'incremental'],
                              help='Type of backup')
    backup_parser.add_argument('--hours', type=int, default=24,
                              help='For incremental: hours to look back')

    # Analyze command
    subparsers.add_parser('analyze', help='Analyze database')

    # Optimize command
    optimize_parser = subparsers.add_parser('optimize', help='Optimize database')
    optimize_parser.add_argument('--compress-attachments', action='store_true',
                                help='Compress old attachments')
    optimize_parser.add_argument('--vacuum', action='store_true',
                                help='Vacuum database')
    optimize_parser.add_argument('--days', type=int, default=30,
                                help='Compress attachments older than N days')

    # Archive command
    archive_parser = subparsers.add_parser('archive', help='Archive old data')
    archive_parser.add_argument('--days', type=int, default=180,
                               help='Archive data older than N days')

    # List command
    subparsers.add_parser('list', help='List backups')

    # Rotate command
    rotate_parser = subparsers.add_parser('rotate', help='Rotate old backups')
    rotate_parser.add_argument('--keep-daily', type=int, default=7,
                              help='Daily backups to keep')
    rotate_parser.add_argument('--keep-weekly', type=int, default=4,
                              help='Weekly backups to keep')
    rotate_parser.add_argument('--keep-monthly', type=int, default=6,
                              help='Monthly backups to keep')

    # Restore command
    restore_parser = subparsers.add_parser('restore', help='Restore backup')
    restore_parser.add_argument('backup_name', help='Backup filename to restore')
    restore_parser.add_argument('--target', help='Target database path')

    args = parser.parse_args()

    manager = DatabaseManager()

    try:
        if args.command == 'backup':
            if args.type == 'full':
                manager.backup_full()
            elif args.type == 'critical':
                manager.backup_critical()
            elif args.type == 'incremental':
                manager.backup_incremental(args.hours)

        elif args.command == 'analyze':
            analysis = manager.analyze_database()

            print("\n" + "=" * 80)
            print("DATABASE ANALYSIS")
            print("=" * 80)

            print(f"\nTotal Size: {format_file_size(analysis['total_size'])}")

            print("\nTop Tables by Size:")
            for table, info in sorted(analysis['tables'].items(),
                                     key=lambda x: x[1]['size'], reverse=True)[:10]:
                print(f"  {table:30} {info['size_formatted']:>10}")

            print("\nAttachment Statistics:")
            att = analysis['attachments']
            print(f"  Count: {att['count']}")
            print(f"  Average Size: {format_file_size(int(att['avg_size']))}")
            print(f"  Maximum Size: {format_file_size(int(att['max_size']))}")
            print(f"  Total Size: {format_file_size(int(att['total_size']))}")

            print("\nDatabase Fragmentation:")
            frag = analysis['fragmentation']
            print(f"  Total Pages: {frag['total_pages']}")
            print(f"  Free Pages: {frag['free_pages']}")
            print(f"  Fragmentation: {frag['fragmentation_percent']:.1f}%")

            if analysis['recommendations']:
                print("\nRecommendations:")
                for rec in analysis['recommendations']:
                    print(f"  • {rec}")

        elif args.command == 'optimize':
            if args.compress_attachments:
                manager.compress_attachments(args.days)

            if args.vacuum:
                manager.vacuum_database()

            if not args.compress_attachments and not args.vacuum:
                print("Specify --compress-attachments and/or --vacuum")

        elif args.command == 'archive':
            manager.archive_old_data(args.days)

        elif args.command == 'list':
            backups = manager.list_backups()

            print("\n" + "=" * 80)
            print("AVAILABLE BACKUPS")
            print("=" * 80)
            print(f"\n{'Type':<12} {'Name':<40} {'Size':>10} {'Created'}")
            print("-" * 80)

            for backup in backups:
                print(f"{backup['type']:<12} {backup['name'][:40]:<40} {backup['size_formatted']:>10} {backup['created'].strftime('%Y-%m-%d %H:%M')}")

            print(f"\nTotal: {len(backups)} backups")

        elif args.command == 'rotate':
            manager.rotate_backups(args.keep_daily, args.keep_weekly, args.keep_monthly)

        elif args.command == 'restore':
            backup_path = manager.backup_dir / args.backup_name
            target = Path(args.target) if args.target else None
            manager.restore_backup(backup_path, target)

        else:
            parser.print_help()

    except KeyboardInterrupt:
        print("\nInterrupted")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()