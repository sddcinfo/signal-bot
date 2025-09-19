# Signal Bot Architecture

## System Overview

Signal Bot is a modular Python application that interfaces with Signal messenger to provide automated responses, message processing, and group management capabilities.

```
┌─────────────────────────────────────────────────────────┐
│                    User Interface                        │
│                   (Web Dashboard)                        │
└────────────────────┬────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────┐
│                   Web Server                             │
│                (Flask/HTTP Server)                       │
└────────────────────┬────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────┐
│                Service Layer                             │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐  │
│  │Messaging │ │  Setup   │ │Sentiment │ │    AI    │  │
│  │ Service  │ │ Service  │ │ Service  │ │ Provider │  │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘  │
└────────────────────┬────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────┐
│                  Data Layer                              │
│              (SQLite Database)                           │
└────────────────────┬────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────┐
│                Signal CLI                                │
│           (External Process)                             │
└──────────────────────────────────────────────────────────┘
```

## Core Components

### 1. Configuration Layer (`config/`)

**Purpose:** Centralized configuration management

**Components:**
- `settings.py`: Application configuration with env variable support
- `constants.py`: Immutable application constants

**Design Decisions:**
- All configuration in one place for easy management
- Environment variable override capability for deployment flexibility
- Type-safe configuration access

### 2. Utility Layer (`utils/`)

**Purpose:** Shared utilities and helpers

**Components:**
- `common.py`: Common helper functions
- `logging.py`: Centralized logging setup
- `validators.py`: Input validation functions
- `decorators.py`: Reusable function decorators
- `bot_instance.py`: Singleton instance management
- `qrcode_generator.py`: QR code generation

**Design Patterns:**
- Decorator pattern for cross-cutting concerns
- Factory pattern for logger creation
- Singleton pattern for instance management

### 3. Service Layer (`services/`)

**Purpose:** Business logic implementation

**Components:**
- `base.py`: Abstract base class for all services
- `messaging.py`: Message handling and processing
- `setup.py`: Initial setup and configuration
- `ai_provider.py`: AI integration (Ollama, OpenAI, etc.)
- `sentiment.py`: Sentiment analysis
- `summarization.py`: Message summarization

**Design Patterns:**
- Template Method pattern in BaseService
- Strategy pattern for AI providers
- Chain of Responsibility for message processing

### 4. Data Layer (`models/`)

**Purpose:** Data persistence and management

**Components:**
- `database.py`: Database connection and query management
- `user_display_utils.py`: User data formatting utilities

**Design Decisions:**
- SQLite for simplicity and portability
- Connection pooling for performance
- Prepared statements for security

### 5. Web Layer (`web/`)

**Purpose:** HTTP interface and web dashboard

**Structure:**
```
web/
├── server.py          # Main web server
├── pages/             # Individual page modules
│   ├── dashboard.py
│   ├── users.py
│   ├── groups.py
│   ├── messages.py
│   ├── settings.py
│   ├── setup.py
│   └── ai_config.py
└── shared/           # Shared web components
    ├── base_page.py  # Base class for pages
    └── templates.py  # HTML templates
```

**Design Patterns:**
- MVC pattern for web interface
- Template pattern for page rendering
- Factory pattern for page creation

## Data Flow

### 1. Incoming Message Flow

```
Signal Message
    ↓
Signal CLI (receive)
    ↓
Signal Service (poll)
    ↓
Message Processor
    ↓
Database (store)
    ↓
AI Service (if needed)
    ↓
Response Generator
    ↓
Signal CLI (send)
    ↓
Signal Network
```

### 2. Web Request Flow

```
HTTP Request
    ↓
Web Server
    ↓
Route Handler
    ↓
Page Module
    ↓
Service Layer
    ↓
Database
    ↓
HTML Response
```

## Database Schema

### Core Tables

1. **users**
   - UUID-based identification
   - Phone numbers and profile information
   - Configuration (emoji, role)
   - Activity tracking

2. **groups**
   - Group identification and metadata
   - Monitoring status
   - Member count tracking

3. **messages**
   - Message content and metadata
   - Sender/recipient relationships
   - Timestamps and processing status

4. **group_members**
   - Many-to-many relationship
   - Join/leave tracking

5. **config**
   - Key-value configuration store
   - Runtime settings

## Service Patterns

### BaseService Pattern

All services inherit from `BaseService` which provides:

```python
class BaseService:
    - Standardized initialization
    - Logger setup
    - Database connection
    - Configuration access
    - Health checks
    - Graceful shutdown
```

### Error Handling Strategy

1. **Service Level:** Try-catch with logging
2. **API Level:** Error response with status codes
3. **Database Level:** Transaction rollback
4. **User Level:** Friendly error messages

### Logging Strategy

- **Module-specific loggers:** Each module has its own logger
- **Structured logging:** Consistent format across application
- **Log levels:** DEBUG, INFO, WARNING, ERROR, CRITICAL
- **File and console output:** Dual logging for production/development

## Security Considerations

### 1. Input Validation

- All user inputs validated
- SQL injection prevention via prepared statements
- Command injection prevention in subprocess calls

### 2. Authentication

- Signal CLI handles authentication
- Bot instance locking prevents multiple instances

### 3. Data Protection

- No password storage
- Sensitive data not logged
- Environment variables for secrets

## Performance Optimizations

### 1. Database

- Indexes on frequently queried columns
- Connection pooling
- Batch operations where possible
- Query optimization

### 2. Caching

- Decorator-based caching
- TTL-based expiration
- Memory-efficient data structures

### 3. Message Processing

- Asynchronous processing where possible
- Rate limiting
- Batch processing for bulk operations

## Deployment Architecture

### Production Setup

```
┌─────────────────┐
│   Nginx/Apache  │ (Optional reverse proxy)
└────────┬────────┘
         │
┌────────▼────────┐
│   Web Server    │ (Port 8084)
└─────────────────┘
         │
┌────────▼────────┐
│ Signal Service  │ (Background process)
└─────────────────┘
         │
┌────────▼────────┐
│   Signal CLI    │ (System service)
└─────────────────┘
```

### Process Management

- **systemd** services for production
- **Process monitoring** for reliability
- **Log rotation** for disk management
- **Backup strategy** for data persistence

## Scalability Considerations

### Horizontal Scaling

- Stateless service design
- Database as single source of truth
- Load balancer compatible

### Vertical Scaling

- Efficient memory usage
- CPU-optimized operations
- I/O optimization

## Future Enhancements

### Planned Improvements

1. **Message Queue:** Add Redis/RabbitMQ for async processing
2. **Webhooks:** Support for external integrations
3. **Plugins:** Extensible architecture for custom features
4. **Analytics:** Advanced reporting and insights
5. **Multi-tenancy:** Support for multiple bot instances

### Technical Debt

1. **Testing:** Increase test coverage
2. **Documentation:** API documentation generation
3. **Monitoring:** Add APM and metrics collection
4. **Migration:** Database migration system

## Development Workflow

### Local Development

```bash
1. Start virtual environment
2. Run database migrations
3. Start signal service
4. Start web server
5. Access dashboard at http://localhost:8084
```

### Testing Strategy

- **Unit tests:** Individual component testing
- **Integration tests:** Component interaction testing
- **End-to-end tests:** Full workflow testing
- **Performance tests:** Load and stress testing

## Monitoring and Observability

### Logging

- Application logs
- Access logs
- Error logs
- Audit logs

### Metrics

- Message processing rate
- Response times
- Error rates
- Resource usage

### Health Checks

- Service availability
- Database connectivity
- Signal CLI status
- AI provider availability

## Disaster Recovery

### Backup Strategy

- Daily database backups
- Configuration backups
- Log archival

### Recovery Procedures

1. Service restart procedures
2. Database restoration
3. Configuration recovery
4. Message replay capabilities

## Conclusion

The Signal Bot architecture is designed for:
- **Modularity:** Easy to extend and maintain
- **Reliability:** Robust error handling and recovery
- **Performance:** Optimized for message processing
- **Security:** Safe handling of user data
- **Scalability:** Ready for growth

This architecture supports both current requirements and future enhancements while maintaining code quality and operational excellence.