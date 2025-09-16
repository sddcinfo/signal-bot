# Signal Bot

A UUID-based Signal bot that automatically sends emoji reactions to messages from configured users in monitored groups, with sentiment analysis and activity visualization capabilities.

## Features

- **Automatic Emoji Reactions**: Bot reacts to messages from specific users with configured emojis
- **UUID-based Architecture**: Uses Signal UUIDs as primary identifiers for reliability
- **Web Management Interface**: Full-featured web UI for configuration and monitoring
- **Attachment Support**: Downloads and stores message attachments with thumbnails in web view
- **Group Membership Sync**: Automatically syncs group memberships from Signal
- **Message History**: View and filter messages from monitored groups with member-level filtering
- **Attachment Filtering**: Filter to show only messages with attachments
- **Sentiment Analysis**: AI-powered emotion and mood analysis of group conversations using Gemini
- **Message Summarization**: Anonymous AI-powered summaries of recent group conversations
- **Activity Visualization**: Hourly bar charts showing message patterns throughout the day
- **Smart Message Handling**: Properly identifies and handles text, attachments, stickers, and reactions
- **Thread-safe Operations**: SQLite with proper locking for concurrent access
- **Clean Setup Flow**: Device linking → group sync → user discovery → configuration
- **Timezone Support**: All timestamps properly converted to user's local timezone
- **Configurable Logging**: Debug flag for verbose output when troubleshooting

## Quick Start

1. **Install signal-cli** (required):
   ```bash
   ./install_signal_cli.sh
   ```

2. **Run the bot**:
   ```bash
   python3 signal_bot.py
   ```

3. **Access web interface**:
   Open http://YOUR_SERVER:8084 in your browser

**Note**: No Python dependencies needed! The bot uses only standard library modules.

## Command-Line Options

```bash
python3 signal_bot.py [options]

Options:
  --sync-groups    Sync group memberships from Signal on startup
  --sync-only      Only sync group memberships and exit (useful for cron)
  --web-only       Start only the web interface without message polling
  --debug          Enable debug logging for troubleshooting
  --help           Show help message
```

## Setup Flow

1. **Device Linking**: Link your Signal device via QR code
2. **Group Discovery**: Automatically discover all Signal groups
3. **Group Monitoring**: Select which groups to monitor for messages
4. **User Configuration**: Set emoji reactions for specific users
5. **Start Polling**: Bot begins watching for messages and sending reactions

## Web Interface Pages

Access the web interface at http://YOUR_SERVER:8084:

- **Overview** (`/`): Dashboard with bot status and statistics
- **Groups** (`/groups`): View all groups, enable/disable monitoring, see member counts
- **Users** (`/users`): Configure emoji reactions for users, manage discovered users
- **All Messages** (`/all-messages`): View message history with group and member filtering
- **Sentiment** (`/sentiment`): AI-powered sentiment analysis of group conversations
- **Summary** (`/summary`): Anonymous AI-powered summaries of recent group conversations
- **Activity** (`/activity`): Visualize hourly message patterns with interactive bar charts

## How It Works

1. **Message Polling**: Bot polls Signal for new messages every 30 seconds
2. **Group Check**: Only processes messages from monitored groups
3. **User Check**: Checks if the sender has configured emoji reactions
4. **Reaction Sending**: Automatically sends the configured emoji as a reaction
5. **Message Storage**: Stores message history for viewing in web interface

## Configuration

### Monitoring Groups
1. Go to the Groups page
2. Click "Monitor" on groups you want to watch
3. Only messages from monitored groups will trigger reactions

### Configuring User Reactions
1. Go to the Users page
2. Find the user you want to configure
3. Click "Configure" and select emojis
4. Choose reaction mode (random, sequential, AI)
5. Save the configuration

### Message Filtering
- In All Messages page, filter by specific groups
- When a group is selected, filter further by individual members
- Use "Show only attachments" checkbox to view messages with attachments
- View detailed message history with sender information
- Attachments are displayed inline with thumbnails for images
- Full pagination support with maintained filter states

### Sentiment Analysis
1. Go to the Sentiment page
2. Select a monitored group
3. Select a date to analyze (defaults to today)
4. Click "Analyze Sentiment" or "Force Refresh"
5. View AI-powered analysis of emotions, mood patterns, and conversation themes
6. Results are cached for efficiency with timezone-aware processing

### Message Summarization
1. Go to the Summary page
2. Select a monitored group
3. Choose how many hours to look back (default: 24)
4. Click "Generate Summary" to get an AI-powered anonymous summary
5. View key topics, important information, action items, and conversation tone
6. All summaries are fully anonymous with no user identifiers
7. Timestamps are displayed in your browser's timezone for consistency

### Activity Visualization
1. Go to the Activity page
2. Select a date to analyze
3. View hourly message distribution as bar charts
4. Each monitored group gets its own color-coded chart
5. Timezone-aware hour calculations based on browser location

## Architecture

- **Main Bot** (`signal_bot.py`): Main orchestrator with threading and message polling
- **Database** (`models/database.py`): UUID-based SQLite operations with sentiment caching
- **Messaging Service** (`services/messaging.py`): Message polling and reaction sending
- **Setup Service** (`services/setup.py`): Device linking and configuration
- **Sentiment Service** (`services/sentiment.py`): AI-powered sentiment analysis using Gemini
- **Summarization Service** (`services/summarization.py`): Anonymous message summarization using Gemini
- **Web Server** (`web/server.py`): Full-featured management interface with standardized UI
- **QR Generator** (`utils/qrcode_generator.py`): ASCII QR code generation

## Database Schema

The bot uses a UUID-centric design:
- **users**: UUID as primary key, stores phone numbers, display names, and friendly names
- **groups**: Tracks all Signal groups with monitoring status and member counts
- **group_members**: Maps users to their group memberships
- **user_reactions**: Stores emoji configurations for each user
- **processed_messages**: Tracks all messages to avoid duplicates
- **messages**: Stores full message history with text content
- **attachments**: Stores message attachments with file data as BLOBs
- **sentiment_analysis**: Caches AI-powered sentiment analysis results

## Requirements

- Python 3.8+
- signal-cli (installed via `./install_signal_cli.sh`)
- SQLite3 (included with Python)
- Web browser for management interface
- Gemini CLI (optional, for sentiment analysis features)

## Troubleshooting

### Bot not receiving messages
- Ensure signal-cli is properly linked: Check Setup page
- Verify groups are monitored: Check Groups page
- Check logs: `tail -f signal_bot.log`
- Enable debug logging: `python3 signal_bot.py --debug`

### Reactions not being sent
- Verify user has reactions configured: Check Users page
- Ensure user is sending messages in monitored groups
- Check that reactions are enabled for the user

### Attachments not displaying
- Check that attachment was properly downloaded from signal-cli
- Verify attachment exists in database: check logs for storage confirmation
- Ensure web server can serve the attachment endpoint

### Group memberships not showing
- Run sync: `python3 signal_bot.py --sync-only`
- Or restart bot with sync: `python3 signal_bot.py --sync-groups`

### Too many debug messages in logs
- By default, bot runs with INFO level logging
- Add `--debug` flag only when troubleshooting issues

## License

MIT