#!/usr/bin/env python3
"""
AI Analysis Types Manager for Signal Bot

This script helps manage AI analysis types for the Signal Bot system.
It provides an easy way to:
- List existing analysis types
- Add new analysis types
- Edit existing analysis types
- Delete analysis types
- Export/import analysis types for backup or sharing
- Set up recommended presets

Usage:
    ./manage_ai_types.py list              # List all analysis types
    ./manage_ai_types.py add               # Interactive add new type
    ./manage_ai_types.py edit <id>         # Edit existing type
    ./manage_ai_types.py delete <id>       # Delete analysis type
    ./manage_ai_types.py export            # Export to JSON
    ./manage_ai_types.py import <file>     # Import from JSON
    ./manage_ai_types.py presets           # Install recommended presets
    ./manage_ai_types.py examples          # Show example configurations
"""

import sys
import json
import argparse
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from models.database import DatabaseManager


class AIAnalysisTypesManager:
    """Manager for AI Analysis Types."""

    # Example preset analysis types for common use cases
    PRESET_TYPES = [
        {
            "name": "summary",
            "display_name": "Message Summary",
            "description": "Comprehensive summary of conversation topics and key points",
            "prompt_template": """Analyze the following chat conversation from the last {hours} hours and provide a comprehensive summary.

Group: {group_name}
Time Period: Last {hours} hours
Message Count: {message_count}

Chat Messages:
{messages}

Please provide a structured summary including:
1. **Key Topics Discussed**: Main subjects and themes of conversation
2. **Important Information**: Any decisions, announcements, or critical details
3. **Action Items**: Any tasks, commitments, or follow-ups mentioned
4. **Overall Activity**: General conversation patterns and flow
5. **Tone & Sentiment**: Overall mood and energy of the conversation
6. **Notable Moments**: Interesting, funny, or significant exchanges

Format the response as clear, concise bullet points under each section.
If a section has no relevant content, you can skip it.
Keep the summary focused on what would be most useful for someone who missed the conversation.""",
            "is_active": True,
            "is_builtin": False,
            "max_hours": 24,
            "min_messages": 5,
            "icon": "📝",
            "color": "#007bff"
        },
        {
            "name": "sentiment",
            "display_name": "Sentiment Analysis",
            "description": "Analyze the emotional tone and mood of conversations",
            "prompt_template": """Analyze the emotional tone and sentiment of the following conversation from the last {hours} hours.

Group: {group_name}
Time Period: Last {hours} hours
Message Count: {message_count}

Chat Messages:
{messages}

Please provide:
1. **Overall Sentiment**: General emotional tone (positive/negative/neutral)
2. **Mood Evolution**: How the conversation mood changed over time
3. **Individual Sentiments**: Key emotional moments from different participants
4. **Emotional Highlights**: Most positive and negative moments
5. **Group Dynamics**: How people interact emotionally with each other

Use specific examples from the conversation to support your analysis.""",
            "is_active": True,
            "is_builtin": False,
            "max_hours": 24,
            "min_messages": 5,
            "icon": "😊",
            "color": "#28a745"
        },
        {
            "name": "topics",
            "display_name": "Topic Extraction",
            "description": "Extract and categorize main discussion topics",
            "prompt_template": """Extract and categorize the main topics discussed in the following conversation from the last {hours} hours.

Group: {group_name}
Time Period: Last {hours} hours
Message Count: {message_count}

Chat Messages:
{messages}

Please provide:
1. **Main Topics**: List the primary subjects discussed with brief descriptions
2. **Topic Categories**: Group topics into relevant categories
3. **Topic Frequency**: Which topics were discussed most
4. **Topic Evolution**: How topics changed throughout the conversation
5. **Related Topics**: Connections between different discussion points

Format as a clear, organized list with relevant context for each topic.""",
            "is_active": True,
            "is_builtin": False,
            "max_hours": 24,
            "min_messages": 5,
            "icon": "🏷️",
            "color": "#17a2b8"
        },
        {
            "name": "highlights",
            "display_name": "Daily Highlights",
            "description": "Extract the most important or interesting moments",
            "prompt_template": """Review the following conversation from the last {hours} hours and extract the most important or interesting highlights.

Group: {group_name}
Time Period: Last {hours} hours
Message Count: {message_count}

Chat Messages:
{messages}

Please identify:
1. **Key Moments**: The most important or significant exchanges
2. **Interesting Discussions**: Notable or engaging conversations
3. **Important Announcements**: Any news, updates, or decisions shared
4. **Memorable Quotes**: Funny, insightful, or notable statements
5. **Context**: Brief context for why each highlight is significant

Focus on what would be most interesting or important for someone catching up on the conversation.""",
            "is_active": True,
            "is_builtin": False,
            "max_hours": 24,
            "min_messages": 5,
            "icon": "⭐",
            "color": "#ffc107"
        },
        {
            "name": "action_items",
            "display_name": "Action Items & Tasks",
            "description": "Extract tasks, to-dos, and commitments from conversations",
            "prompt_template": """Review the following conversation and extract all action items, tasks, and commitments.

Group: {group_name}
Time Period: Last {hours} hours
Message Count: {message_count}

Chat Messages:
{messages}

Please identify:
1. **Tasks Mentioned**: Any to-dos or tasks discussed
2. **Assignments**: Who is responsible for what
3. **Deadlines**: Any mentioned timelines or due dates
4. **Commitments**: Promises or commitments made
5. **Follow-ups Needed**: Items requiring future action

Format as a clear action list with assignee (if mentioned) and any relevant details.""",
            "is_active": True,
            "is_builtin": False,
            "max_hours": 48,
            "min_messages": 3,
            "icon": "✅",
            "color": "#dc3545"
        },
        {
            "name": "meeting_notes",
            "display_name": "Meeting Notes",
            "description": "Generate structured meeting notes from chat discussions",
            "prompt_template": """Generate structured meeting notes from the following conversation.

Group: {group_name}
Time Period: Last {hours} hours
Message Count: {message_count}

Chat Messages:
{messages}

Please create professional meeting notes including:
1. **Meeting Overview**: Main purpose and topics
2. **Attendees**: Active participants (use first names only)
3. **Discussion Points**: Key items discussed
4. **Decisions Made**: Any conclusions or decisions reached
5. **Action Items**: Tasks assigned with owners if mentioned
6. **Next Steps**: Future plans or follow-up items

Format as professional meeting minutes that could be shared with stakeholders.""",
            "is_active": True,
            "is_builtin": False,
            "max_hours": 4,
            "min_messages": 10,
            "icon": "📋",
            "color": "#6c757d"
        },
        {
            "name": "context_brief",
            "display_name": "Context Brief",
            "description": "Quick context for joining an ongoing conversation",
            "prompt_template": """Provide a quick context brief for someone joining this ongoing conversation.

Group: {group_name}
Time Period: Last {hours} hours
Message Count: {message_count}

Chat Messages:
{messages}

Create a brief that includes:
1. **Current Topic**: What's being discussed right now
2. **Background**: Essential context to understand the discussion
3. **Key Points**: Important information shared recently
4. **Active Participants**: Who's involved in the current discussion
5. **Jump-in Points**: How someone could contribute to the conversation

Keep it concise - aim for something that can be read in 30 seconds.""",
            "is_active": True,
            "is_builtin": False,
            "max_hours": 2,
            "min_messages": 5,
            "icon": "🔍",
            "color": "#6610f2"
        },
        {
            "name": "weekly_report",
            "display_name": "Weekly Activity Report",
            "description": "Comprehensive weekly activity analysis",
            "prompt_template": """Generate a comprehensive weekly activity report for the following conversation data.

Group: {group_name}
Time Period: Last {hours} hours (Weekly Report)
Message Count: {message_count}

Chat Messages:
{messages}

Please provide:
1. **Activity Overview**: Message volume, active days/times, participation levels
2. **Key Topics This Week**: Main subjects and themes discussed
3. **Important Developments**: Significant events, decisions, or changes
4. **Team/Group Highlights**: Notable contributions or achievements
5. **Trends**: Changes compared to typical activity patterns
6. **Looking Ahead**: Open items or discussions continuing into next week

Format as an executive summary suitable for team leads or managers.""",
            "is_active": True,
            "is_builtin": False,
            "max_hours": 168,
            "min_messages": 20,
            "icon": "📊",
            "color": "#20c997"
        }
    ]

    def __init__(self):
        """Initialize the AI Analysis Types Manager."""
        self.db = DatabaseManager()
        self._ensure_table_exists()

    def _ensure_table_exists(self):
        """Create the ai_analysis_types table if it doesn't exist."""
        try:
            with self.db._get_connection() as conn:
                cursor = conn.cursor()

                # Create table with all required columns
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS ai_analysis_types (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT NOT NULL UNIQUE,
                        display_name TEXT NOT NULL,
                        description TEXT NOT NULL,
                        prompt_template TEXT NOT NULL,
                        is_active BOOLEAN DEFAULT 1,
                        is_builtin BOOLEAN DEFAULT 0,
                        max_hours INTEGER DEFAULT 24,
                        min_messages INTEGER DEFAULT 5,
                        icon TEXT DEFAULT '📝',
                        color TEXT DEFAULT '#007bff',
                        show_in_ui BOOLEAN DEFAULT 1,
                        show_in_api BOOLEAN DEFAULT 1,
                        requires_auth BOOLEAN DEFAULT 1,
                        requires_group BOOLEAN DEFAULT 0,
                        requires_sender BOOLEAN DEFAULT 0,
                        sort_order INTEGER DEFAULT 100,
                        max_token_limit INTEGER DEFAULT 4000,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)

                # Add missing columns if table already exists (for backward compatibility)
                try:
                    cursor.execute("ALTER TABLE ai_analysis_types ADD COLUMN requires_group BOOLEAN DEFAULT 0")
                except:
                    pass  # Column already exists

                try:
                    cursor.execute("ALTER TABLE ai_analysis_types ADD COLUMN requires_sender BOOLEAN DEFAULT 0")
                except:
                    pass  # Column already exists

                try:
                    cursor.execute("ALTER TABLE ai_analysis_types ADD COLUMN sort_order INTEGER DEFAULT 100")
                except:
                    pass  # Column already exists

                conn.commit()
        except Exception as e:
            print(f"❌ Error creating ai_analysis_types table: {e}")

    def list_types(self, detailed: bool = False) -> List[Dict]:
        """List all AI analysis types."""
        with self.db._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, name, display_name, description, is_active,
                       is_builtin, max_hours, min_messages, icon, color
                FROM ai_analysis_types
                ORDER BY is_builtin DESC, name
            """)

            types = []
            for row in cursor.fetchall():
                type_info = {
                    'id': row[0],
                    'name': row[1],
                    'display_name': row[2],
                    'description': row[3],
                    'is_active': bool(row[4]),
                    'is_builtin': bool(row[5]),
                    'max_hours': row[6],
                    'min_messages': row[7],
                    'icon': row[8],
                    'color': row[9]
                }

                if detailed:
                    cursor.execute(
                        "SELECT prompt_template FROM ai_analysis_types WHERE id = ?",
                        (row[0],)
                    )
                    template_row = cursor.fetchone()
                    if template_row:
                        type_info['prompt_template'] = template_row[0]

                types.append(type_info)

            return types

    def add_type(self, type_data: Dict) -> bool:
        """Add a new AI analysis type."""
        try:
            with self.db._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO ai_analysis_types
                    (name, display_name, description, prompt_template, is_active,
                     is_builtin, max_hours, min_messages, icon, color,
                     show_in_ui, show_in_api, requires_auth, max_token_limit)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, 1, 1, 1)
                """, (
                    type_data['name'],
                    type_data['display_name'],
                    type_data['description'],
                    type_data['prompt_template'],
                    type_data.get('is_active', True),
                    type_data.get('is_builtin', False),
                    type_data.get('max_hours', 24),
                    type_data.get('min_messages', 5),
                    type_data.get('icon', '📝'),
                    type_data.get('color', '#007bff')
                ))
                conn.commit()
                print(f"✅ Successfully added analysis type: {type_data['display_name']}")
                return True
        except Exception as e:
            print(f"❌ Error adding analysis type: {e}")
            return False

    def edit_type(self, type_id: int, type_data: Dict) -> bool:
        """Edit an existing AI analysis type."""
        try:
            with self.db._get_connection() as conn:
                cursor = conn.cursor()

                # Build update query dynamically based on provided fields
                update_fields = []
                values = []

                # Include all editable fields
                for field in ['name', 'display_name', 'description', 'prompt_template',
                            'is_active', 'max_hours', 'min_messages', 'icon', 'color',
                            'requires_group', 'requires_sender', 'sort_order',
                            'anonymize_external', 'include_sender_names']:
                    if field in type_data:
                        update_fields.append(f"{field} = ?")
                        values.append(type_data[field])

                if not update_fields:
                    print("❌ No fields to update")
                    return False

                # Add updated_at timestamp
                update_fields.append("updated_at = CURRENT_TIMESTAMP")

                values.append(type_id)
                query = f"UPDATE ai_analysis_types SET {', '.join(update_fields)} WHERE id = ?"

                cursor.execute(query, values)
                conn.commit()

                if cursor.rowcount > 0:
                    print(f"✅ Successfully updated analysis type ID {type_id}")
                    return True
                else:
                    print(f"❌ Analysis type ID {type_id} not found")
                    return False

        except Exception as e:
            print(f"❌ Error editing analysis type: {e}")
            return False

    def delete_type(self, type_id: int) -> bool:
        """Delete an AI analysis type."""
        try:
            with self.db._get_connection() as conn:
                cursor = conn.cursor()

                # Check if it's a built-in type
                cursor.execute("SELECT is_builtin, display_name FROM ai_analysis_types WHERE id = ?", (type_id,))
                row = cursor.fetchone()

                if not row:
                    print(f"❌ Analysis type ID {type_id} not found")
                    return False

                if row[0]:
                    print(f"❌ Cannot delete built-in analysis type: {row[1]}")
                    return False

                cursor.execute("DELETE FROM ai_analysis_types WHERE id = ?", (type_id,))
                conn.commit()

                print(f"✅ Successfully deleted analysis type: {row[1]}")
                return True

        except Exception as e:
            print(f"❌ Error deleting analysis type: {e}")
            return False

    def export_types(self, filename: str = None) -> str:
        """Export all analysis types to JSON."""
        types = self.list_types(detailed=True)

        if not filename:
            filename = f"ai_analysis_types_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

        with open(filename, 'w') as f:
            json.dump(types, f, indent=2)

        print(f"✅ Exported {len(types)} analysis types to {filename}")
        return filename

    def import_types(self, filename: str) -> int:
        """Import analysis types from JSON."""
        try:
            with open(filename, 'r') as f:
                types = json.load(f)

            imported = 0
            for type_data in types:
                # Remove ID and timestamps
                type_data.pop('id', None)
                type_data.pop('created_at', None)
                type_data.pop('updated_at', None)

                # Check if type already exists
                with self.db._get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute("SELECT id FROM ai_analysis_types WHERE name = ?", (type_data['name'],))
                    if cursor.fetchone():
                        print(f"⚠️  Skipping {type_data['name']} - already exists")
                        continue

                if self.add_type(type_data):
                    imported += 1

            print(f"✅ Imported {imported} analysis types from {filename}")
            return imported

        except Exception as e:
            print(f"❌ Error importing types: {e}")
            return 0

    def install_presets(self) -> int:
        """Install preset analysis types."""
        installed = 0

        for preset in self.PRESET_TYPES:
            # Check if already exists
            with self.db._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT id FROM ai_analysis_types WHERE name = ?", (preset['name'],))
                if cursor.fetchone():
                    print(f"⚠️  Skipping {preset['display_name']} - already exists")
                    continue

            if self.add_type(preset):
                installed += 1

        print(f"\n✅ Installed {installed} preset analysis types")
        return installed

    def interactive_add(self):
        """Interactive mode to add a new analysis type."""
        print("\n=== Add New AI Analysis Type ===\n")

        type_data = {}

        # Required fields
        type_data['name'] = input("Internal name (lowercase, no spaces): ").strip().lower().replace(' ', '_')
        type_data['display_name'] = input("Display name: ").strip()
        type_data['description'] = input("Description: ").strip()

        print("\nPrompt template (enter multiple lines, end with 'END' on its own line):")
        prompt_lines = []
        while True:
            line = input()
            if line.strip() == 'END':
                break
            prompt_lines.append(line)
        type_data['prompt_template'] = '\n'.join(prompt_lines)

        # Optional fields with defaults
        type_data['icon'] = input("Icon emoji (default: 📝): ").strip() or '📝'
        type_data['color'] = input("Color hex (default: #007bff): ").strip() or '#007bff'

        max_hours = input("Max hours to analyze (default: 24): ").strip()
        type_data['max_hours'] = int(max_hours) if max_hours else 24

        min_messages = input("Minimum messages required (default: 5): ").strip()
        type_data['min_messages'] = int(min_messages) if min_messages else 5

        is_active = input("Active? (y/n, default: y): ").strip().lower()
        type_data['is_active'] = is_active != 'n'

        print("\n--- Preview ---")
        print(f"Name: {type_data['name']}")
        print(f"Display: {type_data['display_name']}")
        print(f"Description: {type_data['description']}")
        print(f"Icon: {type_data['icon']} | Color: {type_data['color']}")
        print(f"Max hours: {type_data['max_hours']} | Min messages: {type_data['min_messages']}")
        print(f"Active: {type_data['is_active']}")

        confirm = input("\nAdd this analysis type? (y/n): ").strip().lower()
        if confirm == 'y':
            self.add_type(type_data)
        else:
            print("❌ Cancelled")

    def show_examples(self):
        """Show example analysis type configurations."""
        print("\n=== Example AI Analysis Type Configurations ===\n")

        for i, preset in enumerate(self.PRESET_TYPES[:3], 1):
            print(f"{i}. {preset['display_name']} ({preset['name']})")
            print(f"   Description: {preset['description']}")
            print(f"   Icon: {preset['icon']} | Color: {preset['color']}")
            print(f"   Max hours: {preset['max_hours']}h | Min msgs: {preset['min_messages']}")
            print(f"\n   Prompt Template (first 200 chars):")
            print(f"   {preset['prompt_template'][:200]}...")
            print("-" * 60)

        print("\nUse './manage_ai_types.py presets' to install all preset types")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description='Manage AI Analysis Types for Signal Bot')

    subparsers = parser.add_subparsers(dest='command', help='Commands')

    # List command
    list_parser = subparsers.add_parser('list', help='List all analysis types')
    list_parser.add_argument('-d', '--detailed', action='store_true', help='Show detailed info including prompts')

    # Add command
    add_parser = subparsers.add_parser('add', help='Add a new analysis type (interactive)')

    # Edit command
    edit_parser = subparsers.add_parser('edit', help='Edit an existing analysis type')
    edit_parser.add_argument('id', type=int, help='Analysis type ID to edit')

    # Delete command
    delete_parser = subparsers.add_parser('delete', help='Delete an analysis type')
    delete_parser.add_argument('id', type=int, help='Analysis type ID to delete')

    # Export command
    export_parser = subparsers.add_parser('export', help='Export types to JSON')
    export_parser.add_argument('-f', '--file', help='Output filename')

    # Import command
    import_parser = subparsers.add_parser('import', help='Import types from JSON')
    import_parser.add_argument('file', help='JSON file to import')

    # Presets command
    presets_parser = subparsers.add_parser('presets', help='Install preset analysis types')

    # Examples command
    examples_parser = subparsers.add_parser('examples', help='Show example configurations')

    args = parser.parse_args()

    manager = AIAnalysisTypesManager()

    if args.command == 'list':
        types = manager.list_types(detailed=args.detailed)
        print(f"\n=== AI Analysis Types ({len(types)} total) ===\n")

        for t in types:
            status = "✅" if t['is_active'] else "❌"
            builtin = "🔒" if t['is_builtin'] else ""
            print(f"{t['id']:3d}. {status} {t['icon']} {t['display_name']} ({t['name']}) {builtin}")
            print(f"     {t['description']}")
            print(f"     Hours: {t['max_hours']} | Min msgs: {t['min_messages']} | Color: {t['color']}")

            if args.detailed and 'prompt_template' in t:
                print(f"     Prompt: {t['prompt_template'][:100]}...")
            print()

    elif args.command == 'add':
        manager.interactive_add()

    elif args.command == 'edit':
        # Interactive edit - get detailed info including prompt_template
        types = manager.list_types(detailed=True)
        type_info = next((t for t in types if t['id'] == args.id), None)

        if not type_info:
            print(f"❌ Analysis type ID {args.id} not found")
            sys.exit(1)

        print(f"\n=== Edit Analysis Type: {type_info['display_name']} ===")
        print("Press Enter to keep current value\n")

        updates = {}

        # Edit display name
        new_name = input(f"Display name [{type_info['display_name']}]: ").strip()
        if new_name:
            updates['display_name'] = new_name

        # Edit description
        new_desc = input(f"Description [{type_info['description'][:50]}...]: ").strip()
        if new_desc:
            updates['description'] = new_desc

        # Edit prompt template - show first 100 chars as preview
        print(f"\nCurrent prompt template (first 100 chars):")
        print(f"  {type_info['prompt_template'][:100]}...")
        print("\nEnter new prompt template (or press Enter to keep current):")
        print("(Type 'MULTILINE' to enter multi-line mode, end with '###' on its own line)")

        prompt_input = input().strip()
        if prompt_input:
            if prompt_input == 'MULTILINE':
                print("Enter prompt template (end with '###' on its own line):")
                lines = []
                while True:
                    line = input()
                    if line == '###':
                        break
                    lines.append(line)
                updates['prompt_template'] = '\n'.join(lines)
            else:
                updates['prompt_template'] = prompt_input

        # Edit configuration fields
        new_max_hours = input(f"Max hours to look back [{type_info.get('max_hours', 168)}]: ").strip()
        if new_max_hours:
            updates['max_hours'] = int(new_max_hours)

        new_min_messages = input(f"Minimum messages required [{type_info.get('min_messages', 5)}]: ").strip()
        if new_min_messages:
            updates['min_messages'] = int(new_min_messages)

        # Edit display fields
        new_icon = input(f"Icon [{type_info['icon']}]: ").strip()
        if new_icon:
            updates['icon'] = new_icon

        new_color = input(f"Color [{type_info['color']}]: ").strip()
        if new_color:
            updates['color'] = new_color

        # Edit boolean flags
        new_active = input(f"Is active (1/0) [{type_info.get('is_active', 1)}]: ").strip()
        if new_active:
            updates['is_active'] = int(new_active)

        if updates:
            manager.edit_type(args.id, updates)
        else:
            print("No changes made")

    elif args.command == 'delete':
        confirm = input(f"Are you sure you want to delete analysis type ID {args.id}? (yes/no): ")
        if confirm.lower() == 'yes':
            manager.delete_type(args.id)
        else:
            print("Cancelled")

    elif args.command == 'export':
        manager.export_types(args.file)

    elif args.command == 'import':
        manager.import_types(args.file)

    elif args.command == 'presets':
        manager.install_presets()

    elif args.command == 'examples':
        manager.show_examples()

    else:
        parser.print_help()


if __name__ == '__main__':
    main()