"""
Setup Service for Signal Bot

Handles the complete setup flow:
1. Device linking and bot number detection
2. Group discovery and sync
3. User discovery from groups
4. Clean web interface for configuration

Follows the new UUID-based architecture.
"""
import re
import json
import time
import logging
import subprocess
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass

from models.database import DatabaseManager, User, Group

# Import QR code utilities from the existing utils
try:
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from utils.qrcode_generator import generate_qr_code_data_uri, is_qr_code_available
except ImportError:
    # Fallback if QR utilities not available
    def generate_qr_code_data_uri(data: str, size: int = 8) -> Optional[str]:
        return None
    def is_qr_code_available() -> bool:
        return False


@dataclass
class SignalDevice:
    """Signal device information."""
    phone_number: str
    uuid: str
    is_primary: bool = True


@dataclass
class SignalGroup:
    """Signal group from signal-cli."""
    group_id: str
    name: Optional[str]
    members: List[str]  # List of UUIDs or phone numbers
    is_blocked: bool = False


class SetupService:
    """Manages bot setup and configuration."""

    def __init__(self, db_manager: DatabaseManager, signal_cli_path: str = "/usr/local/bin/signal-cli",
                 logger: Optional[logging.Logger] = None):
        """
        Initialize setup service.

        Args:
            db_manager: Database manager instance
            signal_cli_path: Path to signal-cli executable
            logger: Optional logger instance
        """
        self.db = db_manager
        self.signal_cli_path = signal_cli_path
        self.logger = logger or logging.getLogger(__name__)

        # Track active linking processes
        self.active_linking_processes = []

    def detect_linked_devices(self) -> List[SignalDevice]:
        """
        Detect linked Signal devices using signal-cli.

        Returns:
            List of linked devices with phone numbers and UUIDs
        """
        try:
            cmd = [self.signal_cli_path, "listAccounts"]
            self.logger.debug(f"Executing signal-cli command: {' '.join(cmd)}")
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

            self.logger.debug(f"signal-cli listAccounts result: returncode={result.returncode}")
            self.logger.debug(f"signal-cli listAccounts stdout: {result.stdout}")
            if result.stderr:
                self.logger.debug(f"signal-cli listAccounts stderr: {result.stderr}")

            if result.returncode != 0:
                self.logger.error(f"signal-cli listAccounts failed: {result.stderr}")
                return []

            devices = []
            current_number = None
            current_uuid = None

            for line in result.stdout.strip().split('\n'):
                line = line.strip()

                # Parse phone number
                if line.startswith('Number: '):
                    current_number = line.replace('Number: ', '').strip()

                    # Create device with phone number (UUID may not be available in all cases)
                    if current_number:
                        devices.append(SignalDevice(
                            phone_number=current_number,
                            uuid=current_uuid or "",  # Use empty string if UUID not available
                            is_primary=True
                        ))
                        self.logger.info(f"Found linked device: {current_number}")
                        current_number = None
                        current_uuid = None

                # Parse UUID (optional)
                elif line.startswith('UUID: '):
                    current_uuid = line.replace('UUID: ', '').strip()

            self.logger.info(f"Detected {len(devices)} linked Signal devices")
            return devices

        except subprocess.TimeoutExpired:
            self.logger.error("signal-cli listAccounts timed out")
            return []
        except Exception as e:
            self.logger.error(f"Error detecting linked devices: {e}")
            return []

    def auto_configure_bot(self) -> Optional[SignalDevice]:
        """
        Auto-configure bot by detecting primary linked device.

        Returns:
            Primary device if found, None otherwise
        """
        devices = self.detect_linked_devices()

        if not devices:
            self.logger.warning("No linked Signal devices found")
            return None

        if len(devices) > 1:
            self.logger.warning(f"Multiple devices found ({len(devices)}), using first one")

        primary_device = devices[0]

        # Store bot configuration
        self.db.set_config("bot_phone_number", primary_device.phone_number)
        self.db.set_config("bot_uuid", primary_device.uuid)
        self.db.set_config("signal_cli_path", self.signal_cli_path)

        self.logger.info(f"Bot configured with device: {primary_device.phone_number} ({primary_device.uuid})")
        return primary_device

    def discover_groups(self) -> List[SignalGroup]:
        """
        Discover Signal groups using signal-cli.

        Returns:
            List of available Signal groups
        """
        bot_number = self.db.get_config("bot_phone_number")
        if not bot_number:
            self.logger.error("Bot not configured - cannot discover groups")
            return []

        try:
            cmd = [self.signal_cli_path, "-a", bot_number, "listGroups", "-d"]
            self.logger.debug(f"Executing signal-cli command: {' '.join(cmd)}")
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)

            self.logger.debug(f"signal-cli listGroups result: returncode={result.returncode}")
            self.logger.debug(f"signal-cli listGroups stdout: {result.stdout}")
            if result.stderr:
                self.logger.debug(f"signal-cli listGroups stderr: {result.stderr}")

            if result.returncode != 0:
                self.logger.error(f"signal-cli listGroups failed: {result.stderr}")
                return []

            groups = []

            # Parse single-line group output format
            for line in result.stdout.strip().split('\n'):
                line = line.strip()
                if not line:
                    continue

                self.logger.debug(f"Parsing group line: {line}")

                # Parse single line format: Id: ... Name: ... Description: ... Active: ... Blocked: ... Members: ...
                group_data = {'group_id': None, 'name': None, 'members': [], 'is_blocked': False}

                try:
                    # Extract group ID
                    if 'Id: ' in line:
                        id_start = line.find('Id: ') + 4
                        id_end = line.find(' ', id_start)
                        if id_end == -1:
                            id_end = len(line)
                        group_data['group_id'] = line[id_start:id_end].strip()

                    # Extract group name
                    if 'Name: ' in line:
                        name_start = line.find('Name: ') + 6
                        name_end = line.find(' Description:', name_start)
                        if name_end == -1:
                            name_end = line.find(' Active:', name_start)
                        if name_end == -1:
                            name_end = len(line)
                        group_data['name'] = line[name_start:name_end].strip()

                    # Extract blocked status
                    if 'Blocked: ' in line:
                        blocked_start = line.find('Blocked: ') + 9
                        blocked_end = line.find(' ', blocked_start)
                        if blocked_end == -1:
                            blocked_end = len(line)
                        blocked_str = line[blocked_start:blocked_end].strip()
                        group_data['is_blocked'] = blocked_str.lower() == 'true'

                    # Extract members
                    if 'Members: ' in line:
                        members_start = line.find('Members: ') + 9
                        members_end = line.find('] ', members_start) + 1
                        if members_end == 0:  # '] ' not found, try just ']'
                            members_end = line.find(']', members_start) + 1
                        if members_end > 0:
                            members_str = line[members_start:members_end].strip()
                            if members_str and members_str != '[]':
                                # Parse members list: [uuid1, uuid2, +phone1]
                                members_str = members_str.strip('[]')
                                members = [m.strip().strip('"\'') for m in members_str.split(',') if m.strip()]
                                group_data['members'] = members

                    # Only add if we found a valid group ID
                    if group_data['group_id']:
                        self.logger.debug(f"Parsed group: ID={group_data['group_id']}, Name={group_data['name']}, Members={len(group_data['members'])}, Blocked={group_data['is_blocked']}")
                        groups.append(SignalGroup(
                            group_id=group_data['group_id'],
                            name=group_data['name'],
                            members=group_data['members'],
                            is_blocked=group_data['is_blocked']
                        ))

                except Exception as e:
                    self.logger.warning(f"Failed to parse group line: {line}. Error: {e}")
                    continue

            # Filter out blocked groups
            active_groups = [g for g in groups if not g.is_blocked]

            # DEBUG: Log detailed group information
            self.logger.debug(f"Parsed {len(groups)} total groups from signal-cli output")
            for i, group in enumerate(groups):
                self.logger.debug(f"Group {i}: ID={group.group_id}, Name={group.name}, Members={len(group.members) if group.members else 0}, Blocked={group.is_blocked}")
                if group.members:
                    self.logger.debug(f"  Members: {group.members[:5]}{'...' if len(group.members) > 5 else ''}")

            self.logger.info(f"Discovered {len(active_groups)} active groups (filtered {len(groups) - len(active_groups)} blocked)")
            return active_groups

        except subprocess.TimeoutExpired:
            self.logger.error("signal-cli listGroups timed out")
            return []
        except Exception as e:
            self.logger.error(f"Error discovering groups: {e}")
            return []

    def sync_users_to_database(self) -> int:
        """
        Sync users/contacts from Signal CLI to database with proper friendly names.

        Returns:
            Number of users synced
        """
        try:
            self.logger.info("Getting contacts from Signal CLI...")

            # Get bot phone number for signal-cli command
            bot_phone = self.db.get_config("bot_phone_number")
            if not bot_phone:
                self.logger.error("Bot phone number not configured")
                return 0

            # Run signal-cli listContacts with detailed info
            cmd = [
                self.signal_cli_path,
                "--output=json",
                "-u", bot_phone,
                "listContacts",
                "--detailed"
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

            if result.returncode != 0:
                self.logger.error(f"signal-cli listContacts failed: {result.stderr}")
                return 0

            contacts = []
            if result.stdout.strip():
                try:
                    import json
                    contacts = json.loads(result.stdout)
                except json.JSONDecodeError as e:
                    self.logger.error(f"Error parsing JSON: {e}")
                    return 0

            if not contacts:
                self.logger.info("No contacts found")
                return 0

            self.logger.info(f"Found {len(contacts)} contacts from Signal CLI")

            synced_count = 0
            for contact in contacts:
                uuid = contact.get('uuid')
                phone = contact.get('number')

                # Skip contacts without UUID - these are likely inactive Signal users
                if not uuid:
                    self.logger.debug(f"Skipping contact without UUID: {phone or 'unknown'}")
                    continue

                # Determine friendly name using all available sources
                friendly_name = ""
                if contact.get('name'):
                    friendly_name = contact['name']
                elif contact.get('givenName') and contact.get('familyName'):
                    friendly_name = f"{contact['givenName']} {contact['familyName']}"
                elif contact.get('givenName'):
                    friendly_name = contact['givenName']
                elif contact.get('profile', {}).get('givenName'):
                    friendly_name = contact['profile']['givenName']
                    if contact.get('profile', {}).get('familyName'):
                        friendly_name += f" {contact['profile']['familyName']}"

                try:
                    self.db.upsert_user(
                        uuid=uuid,
                        phone_number=phone,
                        friendly_name=friendly_name
                    )
                    synced_count += 1
                    self.logger.debug(f"Synced user: {friendly_name or phone or uuid}")
                except Exception as e:
                    self.logger.error(f"Error syncing contact {friendly_name or phone or uuid}: {e}")

            self.logger.info(f"Synced {synced_count} users to database")
            return synced_count

        except subprocess.TimeoutExpired:
            self.logger.error("signal-cli listContacts timed out")
            return 0
        except Exception as e:
            self.logger.error(f"Error syncing users: {e}")
            return 0

    def sync_groups_to_database(self, groups: Optional[List[SignalGroup]] = None) -> int:
        """
        Sync discovered groups to database with detailed member information.

        Args:
            groups: Optional list of groups, will discover if not provided

        Returns:
            Number of groups synced
        """
        # If groups not provided, get them from Signal CLI
        if groups is None:
            try:
                self.logger.info("Getting groups from Signal CLI with detailed info...")

                # Get bot phone number for signal-cli command
                bot_phone = self.db.get_config("bot_phone_number")
                if not bot_phone:
                    self.logger.error("Bot phone number not configured")
                    groups = []
                else:
                    # Use JSON output for better parsing
                    cmd = [
                        self.signal_cli_path,
                        "--output=json",
                        "-u", bot_phone,
                        "listGroups",
                        "--detailed"
                    ]

                    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

                    if result.returncode != 0:
                        self.logger.error(f"signal-cli listGroups failed: {result.stderr}")
                        groups = []
                    else:
                        json_groups = []
                        if result.stdout.strip():
                            try:
                                import json
                                json_groups = json.loads(result.stdout)
                            except json.JSONDecodeError as e:
                                self.logger.error(f"Error parsing JSON: {e}")

                        # Convert JSON groups to SignalGroup objects
                        groups = []
                        for jg in json_groups:
                            # Extract member UUIDs
                            member_uuids = []
                            for member in jg.get('members', []):
                                if member.get('uuid'):
                                    member_uuids.append(member['uuid'])

                            groups.append(SignalGroup(
                                group_id=jg.get('id', ''),
                                name=jg.get('name'),
                                members=member_uuids,
                                is_blocked=jg.get('isBlocked', False)
                            ))
            except Exception as e:
                self.logger.error(f"Error getting groups from Signal CLI: {e}")
                groups = []

        # Note: We don't filter empty/test groups here to avoid sync issues
        # Filtering is done at display time in the Groups page

        synced_count = 0

        # Pre-fetch all users to avoid individual profile lookups
        self.logger.info("Pre-loading existing users from database...")
        existing_users = {}
        try:
            # Get all users from database
            with self.db._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT uuid, friendly_name, phone_number FROM users")
                for row in cursor.fetchall():
                    existing_users[row['uuid']] = {
                        'friendly_name': row['friendly_name'],
                        'phone_number': row['phone_number']
                    }
            self.logger.info(f"Loaded {len(existing_users)} existing users")
        except Exception as e:
            self.logger.warning(f"Could not pre-load users: {e}")

        for signal_group in groups:
            try:
                self.logger.debug(f"Starting sync for group: {signal_group.group_id}")

                # Create/update group in database, preserving monitoring status
                self.logger.debug(f"Upserting group: {signal_group.group_id}")
                existing_group = self.db.get_group(signal_group.group_id)
                is_monitored = existing_group.is_monitored if existing_group else False
                group = self.db.upsert_group(
                    group_id=signal_group.group_id,
                    group_name=signal_group.name,
                    member_count=len(signal_group.members),
                    is_monitored=is_monitored
                )
                self.logger.debug(f"Group upsert completed: {signal_group.group_id}")

                # Sync members
                member_uuids = []
                self.logger.debug(f"Processing {len(signal_group.members)} members for group {signal_group.group_id}")

                for i, member_id in enumerate(signal_group.members):
                    self.logger.debug(f"Processing member {i+1}/{len(signal_group.members)}: {member_id}")

                    # Determine if member_id is UUID or phone number
                    if self._is_uuid(member_id):
                        user_uuid = member_id
                        phone_number = None
                        self.logger.debug(f"Member {member_id} is UUID")
                    else:
                        # It's a phone number, we need to find/create UUID
                        # For now, use phone number as UUID (not ideal but works)
                        self.logger.debug(f"Member {member_id} is phone number, converting to UUID")
                        user_uuid = self._phone_to_uuid(member_id)
                        phone_number = member_id
                        self.logger.debug(f"Phone {member_id} -> UUID {user_uuid}")

                    # Use existing user data if available, otherwise create minimal entry
                    # We don't fetch individual profiles during group sync for performance
                    existing_user = existing_users.get(user_uuid)
                    if existing_user:
                        # User exists, use their existing friendly name
                        profile_name = existing_user.get('friendly_name')
                    else:
                        # New user, will get profile on next user sync
                        profile_name = None

                    # Create/update user
                    self.logger.debug(f"Upserting user: {user_uuid}")
                    user = self.db.upsert_user(
                        uuid=user_uuid,
                        phone_number=phone_number,
                        friendly_name=profile_name
                    )
                    self.logger.debug(f"User upsert completed: {user_uuid}")

                    member_uuids.append(user_uuid)

                # Sync group membership
                self.logger.debug(f"Syncing group membership for {signal_group.group_id}")
                self.db.sync_group_members(signal_group.group_id, member_uuids)
                self.logger.debug(f"Group membership sync completed for {signal_group.group_id}")

                synced_count += 1

                self.logger.debug(f"Synced group {signal_group.name} with {len(member_uuids)} members")

            except Exception as e:
                self.logger.error(f"Error syncing group {signal_group.group_id}: {e}")

        self.logger.info(f"Synced {synced_count} groups to database")
        return synced_count

    def clean_import(self) -> Dict[str, Any]:
        """
        Perform a clean import of all contacts and groups from Signal CLI.
        This replaces the separate import_contacts.py script functionality.

        Returns:
            Dictionary with import results
        """
        try:
            self.logger.info("Starting clean import of contacts and groups...")

            # Step 1: Import all users/contacts with friendly names
            self.logger.info("Importing contacts...")
            contacts_imported = self.sync_users_to_database()

            # Step 2: Import all groups with members
            self.logger.info("Importing groups...")
            groups_synced = self.sync_groups_to_database()

            result = {
                'success': True,
                'contacts_imported': contacts_imported,
                'groups_synced': groups_synced
            }

            self.logger.info(f"Clean import complete: {contacts_imported} contacts, {groups_synced} groups")
            return result

        except Exception as e:
            self.logger.error(f"Error during clean import: {e}")
            return {
                'success': False,
                'error': str(e),
                'contacts_imported': 0,
                'groups_synced': 0
            }

    def get_setup_status(self) -> Dict[str, Any]:
        """
        Get current setup status.

        Returns:
            Dictionary with setup status information
        """
        bot_phone = self.db.get_config("bot_phone_number")
        bot_uuid = self.db.get_config("bot_uuid")

        stats = self.db.get_stats()

        # Check if signal-cli is available
        signal_cli_available = self._check_signal_cli()

        return {
            'signal_cli_available': signal_cli_available,
            'signal_cli_path': self.signal_cli_path,
            'bot_configured': bool(bot_phone and bot_uuid),
            'bot_phone_number': bot_phone,
            'bot_uuid': bot_uuid,
            'device_registered': bool(bot_phone and bot_uuid),  # Device is registered if bot is configured
            'groups_synced': stats['total_groups'] > 0,  # Groups are synced if we have any groups
            'total_groups': stats['total_groups'],
            'monitored_groups': stats['monitored_groups'],
            'total_users': stats['total_users'],
            'configured_users': stats['configured_users'],
            'discovered_users': stats['discovered_users'],
            'recent_messages': stats['recent_messages_24h']
        }

    def generate_linking_qr(self, phone_number: str = None) -> Dict[str, Any]:
        """
        Generate QR code for Signal device linking.

        Args:
            phone_number: Optional phone number to link (if not provided, generates anonymous link)

        Returns:
            Dictionary with QR code data and linking URI
        """
        try:
            if phone_number:
                self.logger.info(f"Generating linking QR for {phone_number}")
                # Use signal-cli link command to generate linking URI with phone number
                cmd = [self.signal_cli_path, "link", "-n", phone_number]
            else:
                self.logger.info("Generating anonymous linking QR")
                # Use signal-cli link command without phone number for anonymous linking
                cmd = [self.signal_cli_path, "link"]

            # Use Popen to get output and keep process running for actual linking
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

            # Read output to get linking URI but keep process alive
            linking_uri = None
            try:
                for line in iter(process.stdout.readline, ''):
                    line = line.strip()
                    if line.startswith('sgnl://linkdevice?uuid='):
                        linking_uri = line
                        break

                # If we got the URI, store the process for later cleanup
                # Don't terminate it - the linking process needs it to stay alive
                if linking_uri:
                    # Store process reference for cleanup later
                    self.active_linking_processes.append(process)
                    self.logger.info(f"Started signal-cli link process (PID: {process.pid})")

                    # Start monitoring thread to watch for successful linking
                    import threading
                    monitor_thread = threading.Thread(
                        target=self._monitor_linking_process,
                        args=(process,),
                        daemon=True
                    )
                    monitor_thread.start()

            except Exception as e:
                # Only kill on error
                if process.poll() is None:
                    process.terminate()
                    try:
                        process.wait(timeout=2)
                    except subprocess.TimeoutExpired:
                        process.kill()
                        process.wait()
                raise e

            if linking_uri and linking_uri.startswith('sgnl://linkdevice?uuid='):
                # Generate QR code if available
                qr_data_uri = None
                if is_qr_code_available():
                    qr_data_uri = generate_qr_code_data_uri(linking_uri, size=8)

                self.logger.info(f"Generated linking URI for {phone_number if phone_number else 'anonymous'}")
                return {
                    'success': True,
                    'linking_uri': linking_uri,
                    'qr_code': qr_data_uri,
                    'instructions': 'Scan this QR code with your Signal app to link this device'
                }
            else:
                self.logger.error(f"Could not extract linking URI from signal-cli output: {linking_uri}")
                return {
                    'success': False,
                    'error': 'Could not extract linking URI from signal-cli output'
                }

        except subprocess.TimeoutExpired as e:
            # signal-cli link outputs URI immediately but doesn't exit
            # The URI is usually in stderr when timeout happens
            if e.stderr:
                linking_uri = e.stderr.strip()
                if linking_uri.startswith('sgnl://linkdevice?uuid='):
                    # Generate QR code if available
                    qr_data_uri = None
                    if is_qr_code_available():
                        qr_data_uri = generate_qr_code_data_uri(linking_uri, size=8)

                    self.logger.info(f"Generated linking URI for {phone_number if phone_number else 'anonymous'} (from timeout)")
                    return {
                        'success': True,
                        'linking_uri': linking_uri,
                        'qr_code': qr_data_uri,
                        'instructions': 'Scan this QR code with your Signal app to link this device'
                    }

            self.logger.error("Signal CLI linking process timed out")
            return {
                'success': False,
                'error': 'Signal CLI linking process timed out'
            }
        except Exception as e:
            self.logger.error(f"Error generating linking QR: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    def _monitor_linking_process(self, process):
        """
        Monitor signal-cli link process and automatically complete setup when linking succeeds.

        Args:
            process: The Popen process for signal-cli link
        """
        import time

        self.logger.info("Starting to monitor signal-cli link process for completion...")

        # Monitor for up to 5 minutes
        max_wait_time = 300  # 5 minutes
        check_interval = 5   # Check every 5 seconds
        elapsed_time = 0

        while elapsed_time < max_wait_time:
            try:
                time.sleep(check_interval)
                elapsed_time += check_interval

                # Check if the linking process has completed successfully
                # We do this by trying to detect linked devices
                devices = self.detect_linked_devices()

                if devices:
                    self.logger.info(f"Device linking successful! Found {len(devices)} linked device(s)")

                    # Clean up the linking process
                    if process.poll() is None:
                        self.logger.info("Terminating signal-cli link process after successful linking")
                        process.terminate()
                        try:
                            process.wait(timeout=5)
                        except subprocess.TimeoutExpired:
                            process.kill()
                            process.wait()

                    # Remove from active processes
                    if process in self.active_linking_processes:
                        self.active_linking_processes.remove(process)

                    # Automatically complete the setup process
                    self._complete_automatic_setup(devices)
                    return

            except Exception as e:
                self.logger.error(f"Error during linking monitoring: {e}")
                continue

        # Timeout reached
        self.logger.warning("Device linking monitoring timed out after 5 minutes")

        # Clean up the process
        if process.poll() is None:
            self.logger.info("Terminating signal-cli link process due to timeout")
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()

        # Remove from active processes
        if process in self.active_linking_processes:
            self.active_linking_processes.remove(process)

    def _complete_automatic_setup(self, devices):
        """
        Complete the automatic setup process after successful device linking.

        Args:
            devices: List of detected SignalDevice objects
        """
        try:
            self.logger.info("Starting automatic setup completion...")

            # Step 1: Configure bot with the linked device
            primary_device = devices[0]
            if len(devices) > 1:
                self.logger.warning(f"Multiple devices found ({len(devices)}), using first one")

            # Store bot configuration in database
            self.db.set_config("bot_phone_number", primary_device.phone_number)
            self.db.set_config("bot_uuid", primary_device.uuid)
            self.db.set_config("signal_cli_path", self.signal_cli_path)

            self.logger.info(f"Bot configured with device: {primary_device.phone_number} ({primary_device.uuid})")

            # Step 2: Automatically discover and sync groups
            self.logger.info("Discovering and syncing Signal groups...")
            groups = self.discover_groups()

            if groups:
                # Store discovered groups in database
                self.logger.debug(f"Storing {len(groups)} groups to database...")
                for group in groups:
                    # Only store non-blocked groups
                    if not group.is_blocked:
                        self.logger.debug(f"Storing group: {group.group_id} ({group.name or 'Unknown'})")
                        # Use the database method directly with correct parameters
                        self.db.upsert_group(
                            group_id=group.group_id,
                            group_name=group.name or "Unknown Group",
                            is_monitored=False,  # User can enable monitoring via web interface
                            member_count=len(group.members) if group.members else 0
                        )
                        self.logger.debug(f"Successfully stored group: {group.group_id}")
                    else:
                        self.logger.debug(f"Skipping blocked group: {group.group_id}")

                active_groups = [g for g in groups if not g.is_blocked]
                self.logger.info(f"Discovered {len(active_groups)} active groups (filtered {len(groups) - len(active_groups)} blocked)")
            else:
                self.logger.warning("No groups discovered during automatic setup")

            # Step 3: Discover users from groups (if any groups found)
            total_users = 0
            if groups:
                self.logger.info("Discovering users from groups...")
                for group in groups:
                    if not group.is_blocked and group.members:
                        for member in group.members:
                            # Create user entry (UUID or phone number)
                            if member:  # Skip empty members
                                # Determine if member is UUID or phone number
                                if '@' not in member and not member.startswith('+'):
                                    # Likely a UUID
                                    self.db.upsert_user(
                                        uuid=member,
                                        phone_number=None,
                                        friendly_name=f"User {member}"
                                    )
                                else:
                                    # Likely a phone number
                                    self.db.upsert_user(
                                        uuid=f"phone_{member}",  # Generate UUID for phone-based users
                                        phone_number=member,
                                        friendly_name=f"User {member}"
                                    )
                                total_users += 1

                self.logger.info(f"Discovered {total_users} users from groups")

            # Step 4: Mark setup as complete
            self.logger.debug("Marking setup as complete in database...")
            self.db.set_config("setup_complete", "true")
            self.db.set_config("setup_completed_at", str(int(time.time())))
            self.logger.debug("Setup completion flags stored in database")

            self.logger.info("Automatic setup completed successfully!")
            self.logger.info("Bot is now ready for use. Configure monitoring and reactions through the web interface.")

        except Exception as e:
            self.logger.error(f"Error during automatic setup completion: {e}", exc_info=True)
            # Don't raise - let the bot continue running even if auto-setup fails

    def cleanup_linking_processes(self):
        """Clean up any active linking processes."""
        for process in self.active_linking_processes[:]:  # Copy list to avoid modification during iteration
            try:
                if process.poll() is None:  # Process is still running
                    self.logger.info(f"Terminating signal-cli link process (PID: {process.pid})")
                    process.terminate()
                    try:
                        process.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        self.logger.warning(f"Force killing signal-cli link process (PID: {process.pid})")
                        process.kill()
                        process.wait()
                self.active_linking_processes.remove(process)
            except Exception as e:
                self.logger.error(f"Error cleaning up linking process: {e}")

    def check_linking_completion(self) -> bool:
        """
        Check if any devices have been linked since QR generation.
        Returns True if new devices are detected.
        """
        try:
            current_devices = self.detect_linked_devices()
            return len(current_devices) > 0
        except Exception as e:
            self.logger.error(f"Error checking linking completion: {e}")
            return False

    def complete_device_linking(self, phone_number: str) -> Dict[str, Any]:
        """
        Complete the device linking process and verify it worked.

        Args:
            phone_number: Phone number that was linked

        Returns:
            Dictionary with linking results
        """
        try:
            self.logger.info(f"Completing device linking for {phone_number}")

            # Check if device is now linked
            devices = self.detect_linked_devices()

            for device in devices:
                if device.phone_number == phone_number:
                    # Found the linked device, configure it
                    self.db.set_config("bot_phone_number", device.phone_number)
                    self.db.set_config("bot_uuid", device.uuid)
                    self.db.set_config("signal_cli_path", self.signal_cli_path)

                    self.logger.info(f"Device linking completed successfully for {phone_number}")
                    return {
                        'success': True,
                        'phone_number': device.phone_number,
                        'uuid': device.uuid
                    }

            # Device not found
            self.logger.warning(f"Device linking verification failed for {phone_number}")
            return {
                'success': False,
                'error': 'Device linking verification failed. Please try scanning the QR code again.'
            }

        except Exception as e:
            self.logger.error(f"Error completing device linking: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    def run_initial_setup(self) -> Dict[str, Any]:
        """
        Run complete initial setup process.

        Returns:
            Setup results with status information
        """
        results = {
            'success': False,
            'steps_completed': [],
            'errors': [],
            'setup_status': {},
            'requires_linking': False
        }

        try:
            # Step 1: Check signal-cli
            if not self._check_signal_cli():
                results['errors'].append("signal-cli not available")
                return results
            results['steps_completed'].append("signal_cli_check")

            # Step 2: Auto-configure bot (check for existing devices)
            device = self.auto_configure_bot()
            if not device:
                # No existing device found - generate QR code for linking
                try:
                    qr_result = self.generate_linking_qr()
                    if qr_result['success']:
                        results['requires_linking'] = True
                        results['linking_qr'] = qr_result
                        results['steps_completed'].append("qr_generation")
                        self.logger.info("Generated QR code for device linking")
                    else:
                        results['errors'].append(f"Failed to generate linking QR: {qr_result['error']}")
                        return results
                except Exception as e:
                    results['errors'].append(f"Error generating linking QR: {e}")
                    return results
                return results
            results['steps_completed'].append("device_detection")

            # Step 3: Discover and sync groups
            groups = self.discover_groups()
            if not groups:
                results['errors'].append("No Signal groups found")
                # This is not a fatal error, continue

            synced_count = self.sync_groups_to_database(groups)
            results['steps_completed'].append("group_sync")

            # Step 4: Get final status
            results['setup_status'] = self.get_setup_status()
            results['success'] = True

            self.logger.info(f"Initial setup completed successfully: {device.phone_number}, {synced_count} groups")

        except Exception as e:
            self.logger.error(f"Initial setup failed: {e}")
            results['errors'].append(str(e))

        return results

    def _check_signal_cli(self) -> bool:
        """Check if signal-cli is available and working."""
        try:
            cmd = [self.signal_cli_path, "--version"]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
            return result.returncode == 0
        except Exception:
            return False

    def _detect_bot_uuid(self, bot_phone: str) -> Optional[str]:
        """Detect bot's UUID from signal-cli by parsing receive output."""
        try:
            cmd = [self.signal_cli_path, "-a", bot_phone, "--output=json", "receive", "--timeout", "1"]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

            if result.returncode == 0 and result.stdout:
                # Parse JSON output to find our UUID
                for line in result.stdout.strip().split('\n'):
                    if line.strip():
                        try:
                            data = json.loads(line)
                            if 'envelope' in data and 'sourceUuid' in data['envelope']:
                                # This is our own UUID when we see sync messages
                                source_uuid = data['envelope']['sourceUuid']
                                if self._is_uuid(source_uuid):
                                    return source_uuid
                        except json.JSONDecodeError:
                            continue
            return None
        except Exception as e:
            self.logger.warning(f"Failed to detect bot UUID: {e}")
            return None

    def sync_user_profiles(self, bot_phone: str) -> bool:
        """
        Sync user profile names from Signal CLI contacts.

        Updates the friendly_name field in the database with profile information
        from signal-cli listContacts.
        """
        try:
            self.logger.info("Syncing user profile names from Signal CLI...")

            # Get all contacts with detailed profile information
            cmd = [
                self.signal_cli_path,
                "-a", bot_phone,
                "--output=json",
                "listContacts",
                "--all-recipients",
                "--detailed"
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)

            if result.returncode != 0:
                self.logger.error(f"Failed to list contacts: {result.stderr}")
                return False

            if not result.stdout.strip():
                self.logger.warning("No contacts data received from signal-cli")
                return False

            # Parse JSON contacts data
            import json
            contacts = json.loads(result.stdout)

            updated_count = 0
            for contact in contacts:
                uuid = contact.get("uuid")
                phone = contact.get("number")

                if not uuid:
                    continue

                # Extract all contact fields
                contact_fields = self._extract_contact_fields(contact)

                # Update user in database with all available fields
                success = self.db.upsert_user(
                    uuid=uuid,
                    phone_number=phone,
                    **contact_fields  # Unpack all extracted fields
                )

                if success:
                    updated_count += 1
                    display_name = contact_fields.get('friendly_name', 'Unknown')
                    self.logger.debug(f"Updated profile for {uuid}: {display_name}")

            self.logger.info(f"Profile sync complete - updated {updated_count} user profiles")
            return True

        except Exception as e:
            self.logger.error(f"Failed to sync user profiles: {e}")
            return False

    def _extract_contact_fields(self, contact: dict) -> dict:
        """
        Extract all available contact fields from JSON contact data.

        Returns dict with all fields for upsert_user method.
        """
        # Helper function to safely extract and strip string values
        def safe_strip(value):
            if value is None:
                return None
            if isinstance(value, str):
                stripped = value.strip()
                return stripped if stripped else None
            return None

        # Extract contact name (address book name)
        contact_name = safe_strip(contact.get("name"))

        # Extract direct name fields from root level
        root_given_name = safe_strip(contact.get("givenName"))
        root_family_name = safe_strip(contact.get("familyName"))

        # Extract profile name components
        profile = contact.get("profile") or {}
        profile_given_name = safe_strip(profile.get("givenName"))
        profile_family_name = safe_strip(profile.get("familyName"))

        # Choose the best data from root vs profile (prefer whichever has actual data)
        given_name = profile_given_name or root_given_name
        family_name = profile_family_name or root_family_name

        # Also check nickName fields as additional fallback
        if not given_name:
            nick_given = safe_strip(contact.get("nickGivenName"))
            if nick_given:
                given_name = nick_given

        if not family_name:
            nick_family = safe_strip(contact.get("nickFamilyName"))
            if nick_family:
                family_name = nick_family

        # Extract username
        username = safe_strip(contact.get("username"))

        # Use the new improved friendly name calculation (excluding username)
        friendly_name = self._calculate_best_friendly_name({
            'name': contact_name,
            'givenName': given_name,
            'familyName': family_name
        })

        return {
            'contact_name': contact_name,
            'given_name': given_name,
            'family_name': family_name,
            'profile_given_name': profile_given_name,
            'profile_family_name': profile_family_name,
            'username': username,
            'friendly_name': friendly_name
        }

    def _build_friendly_name(self, contact: dict) -> str:
        """
        Build a friendly display name from contact data (for backward compatibility).
        """
        fields = self._extract_contact_fields(contact)
        friendly_name = fields.get('friendly_name')

        if friendly_name:
            return friendly_name

        # Fallback to phone number if available
        phone = contact.get("number") or ""
        phone = phone.strip() if phone else ""
        if phone:
            return f"User {phone[-4:]}"  # Last 4 digits for privacy

        # Final fallback to UUID prefix
        uuid = contact.get("uuid") or ""
        if uuid:
            return f"User {uuid}"

        return "Unknown User"

    def _is_uuid(self, identifier: str) -> bool:
        """Check if identifier is a UUID format."""
        # UUID pattern: 8-4-4-4-12 hex digits
        uuid_pattern = r'^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$'
        return bool(re.match(uuid_pattern, identifier))

    def _phone_to_uuid(self, phone_number: str) -> str:
        """
        Convert phone number to UUID-like identifier.

        This is a temporary solution until we have proper UUID mapping.
        In the real Signal protocol, UUIDs are assigned by the server.
        """
        # Simple hash-based UUID generation from phone number
        import hashlib

        # Remove any non-digit characters
        clean_phone = re.sub(r'\D', '', phone_number)

        # Create a deterministic UUID-like string from phone hash
        phone_hash = hashlib.md5(clean_phone.encode()).hexdigest()

        # Format as UUID: 8-4-4-4-12
        return f"{phone_hash[:8]}-{phone_hash[8:12]}-{phone_hash[12:16]}-{phone_hash[16:20]}-{phone_hash[20:32]}"

    def _fetch_user_profile(self, user_uuid: str) -> Optional[str]:
        """
        Fetch user profile name from Signal-CLI.

        Args:
            user_uuid: The UUID of the user to fetch profile for

        Returns:
            Profile name if found, None otherwise
        """
        try:
            self.logger.debug(f"Fetching profile for user: {user_uuid}")

            # Get bot phone from database
            bot_phone = self.db.get_config("bot_phone_number")
            if not bot_phone:
                self.logger.error("Bot phone number not configured")
                return None

            # Use signal-cli to get user info
            cmd = [
                self.signal_cli_path,
                "-u", bot_phone,
                "getUserStatus",
                user_uuid
            ]

            self.logger.debug(f"Running command: {' '.join(cmd)}")
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=10  # Short timeout for profile fetches
            )

            if result.returncode != 0:
                self.logger.debug(f"Failed to fetch profile for {user_uuid}: {result.stderr}")
                return None

            # Parse the output to extract profile name
            output = result.stdout.strip()
            if not output:
                return None

            # Try to parse JSON output if it's structured
            try:
                import json
                data = json.loads(output)
                if isinstance(data, dict):
                    # Look for profile name in common fields
                    profile_name = (
                        data.get('profileName') or
                        data.get('displayName') or
                        data.get('name') or
                        data.get('givenName')
                    )
                    if profile_name and profile_name.strip():
                        self.logger.debug(f"Found profile name for {user_uuid}: {profile_name}")
                        return profile_name.strip()
            except (json.JSONDecodeError, TypeError):
                # Not JSON, try to extract from plain text
                pass

            # Try alternative command to get contact info using JSON
            cmd_contact = [
                self.signal_cli_path,
                "--output=json",
                "-u", bot_phone,
                "listContacts"
            ]

            self.logger.debug(f"Trying contact list: {' '.join(cmd_contact)}")
            result_contact = subprocess.run(
                cmd_contact,
                capture_output=True,
                text=True,
                timeout=10
            )

            if result_contact.returncode == 0 and result_contact.stdout.strip():
                # Parse the JSON output from listContacts
                try:
                    import json
                    contacts = json.loads(result_contact.stdout.strip())

                    for contact in contacts:
                        if contact.get('uuid') == user_uuid:
                            # Priority: contact name > profile name
                            contact_name_raw = contact.get('name', '')
                            contact_name = contact_name_raw.strip() if contact_name_raw else ''

                            profile = contact.get('profile', {})
                            profile_given_raw = profile.get('givenName', '')
                            profile_given = profile_given_raw.strip() if profile_given_raw else ''

                            profile_family_raw = profile.get('familyName', '')
                            profile_family = profile_family_raw.strip() if profile_family_raw else ''

                            # Build profile name from given + family if available
                            profile_name = ''
                            if profile_given and profile_family:
                                profile_name = f"{profile_given} {profile_family}".strip()
                            elif profile_given:
                                profile_name = profile_given
                            elif profile_family:
                                profile_name = profile_family

                            # Return the best available name (prioritize contact name over profile name)
                            if contact_name:
                                self.logger.debug(f"Found contact name for {user_uuid}: {contact_name}")
                                return contact_name
                            elif profile_name:
                                self.logger.debug(f"Found profile name for {user_uuid}: {profile_name}")
                                return profile_name

                except json.JSONDecodeError as e:
                    self.logger.warning(f"Failed to parse JSON from listContacts: {e}")
                except Exception as e:
                    self.logger.warning(f"Error processing contact JSON: {e}")

            self.logger.debug(f"No profile name found for user: {user_uuid}")
            return None

        except subprocess.TimeoutExpired:
            self.logger.warning(f"Timeout fetching profile for user: {user_uuid}")
            return None
        except Exception as e:
            self.logger.error(f"Error fetching profile for user {user_uuid}: {str(e)}")
            return None

    def clean_import_contacts_and_groups(self, bot_phone: str) -> Dict[str, Any]:
        """
        Clean import of contacts and groups - clears database and reimports from signal-cli.

        This uses listContacts without -a flag to avoid duplicates.

        Returns:
            Dict with import results including counts and any errors
        """
        try:
            self.logger.info("Starting clean import of contacts and groups...")

            # Preserve existing configurations before clearing
            self.logger.info("Preserving existing configurations...")

            # Get monitored groups
            monitored_groups = {}
            with self.db._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT group_id, is_monitored FROM groups WHERE is_monitored = 1")
                for row in cursor.fetchall():
                    monitored_groups[row[0]] = True

                # Get user reactions (using same connection)
                user_reactions = {}
                cursor.execute("SELECT uuid, emojis, reaction_mode, is_active FROM user_reactions")
                for row in cursor.fetchall():
                    user_reactions[row[0]] = {
                        'emojis': json.loads(row[1]) if row[1] else [],
                        'reaction_mode': row[2],
                        'is_active': bool(row[3])
                    }

            # Clear data but preserve configurations
            self.logger.info("Clearing existing users and group memberships...")
            with self.db._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM users")
                cursor.execute("DELETE FROM group_members")
                # Don't delete groups table - preserve monitored status
                # Don't delete user_reactions - will restore after user import
                conn.commit()

            # Import clean contacts (without -a flag to avoid duplicates)
            self.logger.info("Getting clean contact list from Signal CLI...")
            cmd = [
                self.signal_cli_path,
                "--output=json",
                "-u", bot_phone,
                "listContacts",
                "--detailed"
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)

            if result.returncode != 0:
                self.logger.error(f"Failed to list contacts: {result.stderr}")
                return {"success": False, "error": "Failed to list contacts"}

            if not result.stdout.strip():
                self.logger.warning("No contacts data received")
                return {"success": False, "error": "No contacts data received"}

            contacts = json.loads(result.stdout)
            self.logger.info(f"Found {len(contacts)} contacts")

            # Import contacts
            imported_count = 0
            for contact in contacts:
                uuid = contact.get('uuid')
                phone = contact.get('number')

                # Skip contacts without UUID or phone number
                if not uuid and not phone:
                    continue

                # Calculate the best friendly name using improved logic
                friendly_name = self._calculate_best_friendly_name(contact)

                # Generate UUID if missing (for phone-only contacts)
                if not uuid:
                    import uuid as uuid_module
                    uuid = str(uuid_module.uuid4())

                try:
                    self.db.upsert_user(
                        uuid=uuid,
                        phone_number=phone,
                        friendly_name=friendly_name
                    )
                    imported_count += 1
                    self.logger.debug(f"Imported: {friendly_name or phone or uuid}")
                except Exception as e:
                    self.logger.error(f"Error importing contact {friendly_name or phone or uuid}: {e}")

            self.logger.info(f"Imported {imported_count} contacts successfully")

            # Now sync groups
            self.logger.info("Syncing groups...")
            group_cmd = [
                self.signal_cli_path,
                "--output=json",
                "-u", bot_phone,
                "listGroups",
                "--detailed"
            ]

            group_result = subprocess.run(group_cmd, capture_output=True, text=True, timeout=60)

            if group_result.returncode != 0:
                self.logger.error(f"Failed to list groups: {group_result.stderr}")
                return {
                    "success": True,
                    "contacts_imported": imported_count,
                    "groups_synced": 0,
                    "warning": "Groups sync failed"
                }

            groups_synced = 0
            if group_result.stdout.strip():
                groups = json.loads(group_result.stdout)
                self.logger.info(f"Found {len(groups)} groups")

                for group in groups:
                    group_id = group.get('id')
                    group_name = group.get('name', 'Unnamed Group')
                    members = group.get('members', [])

                    if not group_id:
                        continue

                    try:
                        # Update group info - preserve monitored status
                        self.db.upsert_group(
                            group_id=group_id,
                            group_name=group_name,
                            member_count=len(members)
                        )

                        # Restore monitored status if it was preserved
                        if group_id in monitored_groups:
                            self.db.set_group_monitoring(group_id, True)

                        # Sync members
                        member_uuids = []
                        for member in members:
                            member_uuid = member.get('uuid')
                            if member_uuid:
                                member_uuids.append(member_uuid)

                        if member_uuids:
                            self.db.sync_group_members(group_id, member_uuids)

                        groups_synced += 1
                        self.logger.debug(f"Synced group: {group_name} ({len(member_uuids)} members)")

                    except Exception as e:
                        self.logger.error(f"Error syncing group {group_name}: {e}")

            # Restore user reactions for users that were preserved
            self.logger.info("Restoring user reaction configurations...")
            reactions_restored = 0
            for user_uuid, reaction_config in user_reactions.items():
                # Check if this user was reimported
                user = self.db.get_user(user_uuid)
                if user:
                    try:
                        self.db.set_user_reactions(
                            user_uuid,
                            reaction_config['emojis'],
                            reaction_config['reaction_mode']
                        )
                        if not reaction_config['is_active']:
                            # If it was inactive, deactivate it again
                            with self.db._get_connection() as conn:
                                cursor = conn.cursor()
                                cursor.execute(
                                    "UPDATE user_reactions SET is_active = 0 WHERE uuid = ?",
                                    (user_uuid,)
                                )
                                conn.commit()
                        reactions_restored += 1
                    except Exception as e:
                        self.logger.error(f"Error restoring reactions for {user_uuid}: {e}")

            self.logger.info(f"Clean import complete: {imported_count} contacts, {groups_synced} groups, {reactions_restored} reaction configs restored")

            return {
                "success": True,
                "contacts_imported": imported_count,
                "groups_synced": groups_synced,
                "reactions_restored": reactions_restored,
                "message": f"Successfully imported {imported_count} contacts and {groups_synced} groups. Restored {reactions_restored} user reaction configurations."
            }

        except Exception as e:
            self.logger.error(f"Clean import failed: {e}")
            return {
                "success": False,
                "error": f"Clean import failed: {str(e)}"
            }

    def recalculate_friendly_names(self) -> Dict[str, Any]:
        """
        Recalculate friendly names for all users based on current Signal CLI contact data.
        This uses improved logic to prefer the best available name.
        """
        try:
            self.logger.info("Starting friendly name recalculation for all users...")

            # Get current contacts from Signal CLI
            # First get the bot phone number
            devices = self.detect_linked_devices()
            if not devices:
                return {
                    "success": False,
                    "error": "No linked Signal devices found"
                }

            bot_phone = devices[0].phone_number

            # Get contacts using Signal CLI
            self.logger.info("Getting contacts from Signal CLI...")
            cmd = [
                self.signal_cli_path,
                "--output=json",
                "-u", bot_phone,
                "listContacts",
                "--detailed"
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)

            if result.returncode != 0:
                return {
                    "success": False,
                    "error": f"Signal CLI command failed: {result.stderr}"
                }

            try:
                contacts = json.loads(result.stdout)
            except json.JSONDecodeError:
                return {
                    "success": False,
                    "error": "Failed to parse Signal CLI JSON output"
                }

            if not contacts:
                return {
                    "success": False,
                    "error": "No contacts found from Signal CLI"
                }

            # Build a mapping of UUID/phone to contact data
            contact_map = {}
            for contact in contacts:
                uuid = contact.get('uuid')
                phone = contact.get('number')

                if uuid:
                    contact_map[uuid] = contact
                if phone:
                    contact_map[phone] = contact

            # Update friendly names for all users in database
            updated_count = 0
            with self.db._get_connection() as conn:
                cursor = conn.cursor()

                # Get all users
                cursor.execute("SELECT uuid, phone_number, friendly_name FROM users")
                users = cursor.fetchall()

                for user in users:
                    user_uuid = user[0]
                    user_phone = user[1]
                    current_friendly_name = user[2]

                    # Find matching contact data
                    contact_data = None
                    if user_uuid in contact_map:
                        contact_data = contact_map[user_uuid]
                    elif user_phone in contact_map:
                        contact_data = contact_map[user_phone]

                    if contact_data:
                        # Calculate the best friendly name using improved logic
                        new_friendly_name = self._calculate_best_friendly_name(contact_data)

                        # Only update if the name has changed and is not empty
                        if new_friendly_name and new_friendly_name != current_friendly_name:
                            cursor.execute(
                                "UPDATE users SET friendly_name = ? WHERE uuid = ?",
                                (new_friendly_name, user_uuid)
                            )
                            updated_count += 1
                            self.logger.debug(f"Updated {user_uuid}: '{current_friendly_name}' -> '{new_friendly_name}'")

                conn.commit()

            self.logger.info(f"Friendly name recalculation complete: updated {updated_count} users")

            return {
                "success": True,
                "updated_count": updated_count,
                "message": f"Successfully updated {updated_count} user friendly names"
            }

        except Exception as e:
            self.logger.error(f"Friendly name recalculation failed: {e}")
            return {
                "success": False,
                "error": f"Friendly name recalculation failed: {str(e)}"
            }

    def _calculate_best_friendly_name(self, contact: dict) -> str:
        """
        Calculate the best friendly name from contact data using improved priority logic.
        Priority:
        1. Contact name (address book name)
        2. Constructed name from given/family names (root or profile level)
        3. Empty string (no username fallback)
        """
        # Extract all available name fields, handling None values
        name_raw = contact.get('name')
        name = name_raw.strip() if name_raw else ''

        given_name_raw = contact.get('givenName')
        given_name = given_name_raw.strip() if given_name_raw else ''

        family_name_raw = contact.get('familyName')
        family_name = family_name_raw.strip() if family_name_raw else ''

        # Priority 1: Address book contact name (if not empty)
        if name:
            return name

        # Priority 2: Construct name from given/family names
        if given_name and family_name:
            return f"{given_name} {family_name}"
        elif given_name:
            return given_name
        elif family_name:
            return family_name

        # No fallback to username - return empty to use phone/UUID in centralized display logic
        return ""