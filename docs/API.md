# Signal Bot Web API Documentation

## Overview

The Signal Bot provides a RESTful API for managing bot configuration, monitoring status, and accessing message data. The API is available at `http://localhost:8084` by default.

## Base URL

```
http://localhost:8084
```

For testing environment:
```
http://localhost:8085
```

## Authentication

Currently, the API does not require authentication. In production, consider implementing authentication using a reverse proxy.

## API Endpoints

### Core Pages

#### GET /
**Dashboard Overview**

Returns the main dashboard page with bot status and statistics.

**Response:** HTML page

---

#### GET /setup
**Bot Setup Page**

Device linking and initial configuration page.

**Response:** HTML page

---

### User Management

#### GET /users
**Users List Page**

Display all discovered Signal users with emoji configuration options.

**Response:** HTML page

---

#### POST /api/users/sync
**Sync Users from Signal**

Synchronize user list from Signal CLI contacts.

**Request:**
```json
{}
```

**Response:**
```json
{
  "success": true,
  "synced": 105,
  "message": "Synced 105 users"
}
```

---

#### POST /api/users/<uuid>/reactions
**Configure User Reactions**

Set emoji reactions for a specific user.

**Request:**
```json
{
  "emojis": ["👍", "❤️", "😊"],
  "reaction_mode": "random",
  "enabled": true
}
```

**Response:**
```json
{
  "success": true
}
```

**Reaction Modes:**
- `random` - Random emoji from list
- `sequential` - Cycle through emojis
- `ai` - AI-based selection

---

### Group Management

#### GET /groups
**Groups List Page**

Display all Signal groups with monitoring controls.

**Response:** HTML page

---

#### POST /api/groups/sync
**Sync Groups from Signal**

Synchronize groups and memberships from Signal CLI.

**Request:**
```json
{}
```

**Response:**
```json
{
  "success": true,
  "synced": 35,
  "message": "Synced 35 groups"
}
```

---

#### POST /api/groups/<group_id>/monitor
**Toggle Group Monitoring**

Enable or disable monitoring for a specific group.

**Request:**
```json
{
  "monitor": true
}
```

**Response:**
```json
{
  "success": true
}
```

---

### Message Management

#### GET /messages
**Messages Page**

Display message history with filtering options.

**Query Parameters:**
- `group` - Filter by group UUID
- `user` - Filter by user UUID
- `date` - Filter by date (YYYY-MM-DD)
- `tab` - Tab view (all, attachments, mentions, reactions)
- `page` - Page number for pagination

**Response:** HTML page

---

#### GET /api/messages
**Get Messages (JSON)**

Retrieve messages in JSON format.

**Query Parameters:**
- `group` - Filter by group UUID
- `user` - Filter by user UUID
- `date` - Filter by date
- `limit` - Number of messages (default: 100)
- `offset` - Skip messages for pagination

**Response:**
```json
{
  "messages": [
    {
      "id": 1,
      "uuid": "user-uuid",
      "group_id": "group-uuid",
      "timestamp": "2025-09-18T14:00:00Z",
      "text": "Hello world",
      "has_attachment": false
    }
  ],
  "total": 150
}
```

---

#### GET /api/attachments/<message_id>
**Get Message Attachment**

Retrieve attachment data for a specific message.

**Response:** Binary attachment data with appropriate content-type

---

### AI Features

#### GET /sentiment
**Sentiment Analysis Page**

AI-powered sentiment analysis interface.

**Response:** HTML page

---

#### POST /api/sentiment/analyze
**Analyze Group Sentiment**

Perform sentiment analysis on group messages.

**Request:**
```json
{
  "group_id": "group-uuid",
  "date": "2025-09-18",
  "force": false
}
```

**Response:**
```json
{
  "success": true,
  "cached": false,
  "analysis": {
    "overall_sentiment": "positive",
    "emotion_breakdown": {
      "joy": 45,
      "neutral": 35,
      "concern": 20
    },
    "key_themes": ["project updates", "planning"],
    "mood_progression": "improving"
  }
}
```

---

#### GET /summary
**Message Summary Page**

AI-powered message summarization interface.

**Response:** HTML page

---

#### POST /api/summary/generate
**Generate Message Summary**

Create AI summary of recent messages.

**Request:**
```json
{
  "group_id": "group-uuid",
  "hours": 24
}
```

**Response:**
```json
{
  "success": true,
  "summary": {
    "key_topics": ["Release planning", "Bug fixes"],
    "decisions": ["Postpone release to Friday"],
    "action_items": ["Review PR #123", "Update documentation"],
    "participants": 5,
    "message_count": 87
  }
}
```

---

### AI Configuration

#### GET /ai-config
**AI Configuration Page**

Configure AI providers (Ollama, OpenAI, Anthropic, Gemini).

**Response:** HTML page

---

#### POST /api/ai-config/save
**Save AI Configuration**

Update AI provider settings.

**Request:**
```json
{
  "ollama_host": "http://localhost:11434/",
  "ollama_model": "llama3.2:latest",
  "ollama_enabled": true,
  "gemini_enabled": false
}
```

**Response:**
```json
{
  "success": true
}
```

---

#### POST /api/ai-config/preload
**Preload AI Model**

Preload model into memory for faster responses.

**Request:**
```json
{
  "model": "llama3.2:latest"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Model loaded successfully"
}
```

---

#### GET /api/ai-config/status
**Get AI Provider Status**

Check status of configured AI providers.

**Response:**
```json
{
  "ollama": {
    "available": true,
    "loaded_models": ["llama3.2:latest"],
    "memory_usage": "4.2GB"
  },
  "openai": {
    "available": false,
    "reason": "API key not configured"
  }
}
```

---

### Statistics and Monitoring

#### GET /activity
**Activity Visualization Page**

Hourly message activity charts.

**Response:** HTML page

---

#### GET /stats
**Statistics Overview Page**

Comprehensive statistics dashboard.

**Response:** HTML page

---

#### GET /bot-status
**Bot Status Page**

Real-time bot service monitoring.

**Response:** HTML page

---

#### GET /api/status
**Get Bot Status (JSON)**

Retrieve current bot status and health metrics.

**Response:**
```json
{
  "signal_cli": {
    "available": true,
    "version": "0.13.4",
    "phone": "+19095292723"
  },
  "database": {
    "connected": true,
    "users": 105,
    "groups": 35,
    "messages": 15420
  },
  "services": {
    "polling": "running",
    "web_server": "running"
  },
  "uptime": 3600
}
```

---

### Setup and Configuration

#### POST /api/setup/link
**Link Signal Device**

Generate QR code for device linking.

**Request:**
```json
{}
```

**Response:**
```json
{
  "success": true,
  "qr_code": "data:image/png;base64,..."
}
```

---

#### POST /api/setup/register
**Register Phone Number**

Register new Signal account.

**Request:**
```json
{
  "phone": "+1234567890"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Verification code sent"
}
```

---

#### POST /api/setup/verify
**Verify Registration**

Complete registration with verification code.

**Request:**
```json
{
  "phone": "+1234567890",
  "code": "123456"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Registration complete"
}
```

---

### Controls

#### GET /controls
**Bot Controls Page**

Manual bot control interface.

**Response:** HTML page

---

#### POST /api/controls/sync
**Manual Sync**

Trigger manual synchronization.

**Request:**
```json
{
  "type": "all"  // or "users" or "groups"
}
```

**Response:**
```json
{
  "success": true,
  "users_synced": 105,
  "groups_synced": 35
}
```

---

#### POST /api/controls/cleanup
**Database Cleanup**

Clean old messages and optimize database.

**Request:**
```json
{
  "days": 30
}
```

**Response:**
```json
{
  "success": true,
  "deleted": 1250,
  "optimized": true
}
```

---

## Error Responses

All API endpoints return consistent error responses:

```json
{
  "success": false,
  "error": "Error message",
  "details": "Detailed error information"
}
```

**HTTP Status Codes:**
- `200` - Success
- `400` - Bad Request
- `404` - Not Found
- `500` - Internal Server Error

## Data Formats

### Timestamps
All timestamps are in ISO 8601 format with timezone:
```
2025-09-18T14:30:00Z
```

### UUIDs
User and group identifiers use Signal UUIDs:
```
123e4567-e89b-12d3-a456-426614174000
```

### Phone Numbers
Phone numbers include country code:
```
+1234567890
```

## Rate Limiting

Currently no rate limiting is implemented. For production use, consider:
- Nginx rate limiting
- Flask-Limiter
- Custom middleware

## WebSocket Support

Not currently implemented. Future versions may include:
- Real-time message updates
- Live status monitoring
- Push notifications

## Example Usage

### Python

```python
import requests

# Base URL
BASE_URL = "http://localhost:8084"

# Sync users
response = requests.post(f"{BASE_URL}/api/users/sync")
print(f"Synced {response.json()['synced']} users")

# Get messages
params = {
    "group": "group-uuid",
    "date": "2025-09-18",
    "limit": 50
}
response = requests.get(f"{BASE_URL}/api/messages", params=params)
messages = response.json()["messages"]

# Configure user reactions
data = {
    "emojis": ["👍", "❤️"],
    "reaction_mode": "random",
    "enabled": True
}
response = requests.post(
    f"{BASE_URL}/api/users/user-uuid/reactions",
    json=data
)
```

### JavaScript

```javascript
// Sync groups
fetch('/api/groups/sync', {
    method: 'POST',
    headers: {
        'Content-Type': 'application/json'
    }
})
.then(response => response.json())
.then(data => console.log(`Synced ${data.synced} groups`));

// Generate summary
fetch('/api/summary/generate', {
    method: 'POST',
    headers: {
        'Content-Type': 'application/json'
    },
    body: JSON.stringify({
        group_id: 'group-uuid',
        hours: 24
    })
})
.then(response => response.json())
.then(data => console.log(data.summary));
```

### cURL

```bash
# Get bot status
curl http://localhost:8084/api/status

# Sync users
curl -X POST http://localhost:8084/api/users/sync

# Configure AI
curl -X POST http://localhost:8084/api/ai-config/save \
  -H "Content-Type: application/json" \
  -d '{"ollama_host":"http://localhost:11434/","ollama_enabled":true}'
```

## Development

### Adding New Endpoints

1. Create route in appropriate page module (`web/pages/`)
2. Follow RESTful conventions
3. Return consistent JSON responses
4. Update this documentation

### Testing API Endpoints

```bash
# Use the test server
./run_web_server.sh --testing

# Test endpoints
curl http://localhost:8085/api/status
```

## Security Considerations

1. **Authentication**: Implement authentication for production
2. **HTTPS**: Use SSL/TLS in production
3. **Input Validation**: All inputs are validated
4. **SQL Injection**: Using parameterized queries
5. **XSS Prevention**: HTML escaping in templates
6. **CORS**: Configure for your domain

## See Also

- [CONFIGURATION.md](CONFIGURATION.md) - Configuration options
- [ARCHITECTURE.md](ARCHITECTURE.md) - System architecture
- [TROUBLESHOOTING.md](TROUBLESHOOTING.md) - Common issues