# LitePolis-database-particiapi

ParticiAPI-compatible database module for LitePolis. This module extends `LitePolis-database-default` with ParticiAPI-specific models and functionality.

## Overview

This module provides:
- `ParticiapiUser` - Extended participant model with ParticiAPI fields
- `ParticipantExtended` - Additional participant metadata
- `ParticiapiIssuer` - OIDC issuer configuration
- `MathMain` - Math results caching
- `NotificationTasks` - Notification queue management

## Installation

```bash
litepolis-cli deploy add-deps litepolis-database-particiapi
litepolis-cli deploy sync-deps
```

## Configuration

This module shares database configuration with `LitePolis-database-default`. To customize, create a config file:

```bash
litepolis-cli deploy init-config
```

Then edit `~/.litepolis/litepolis.config`:

```ini
[litepolis_database_default]
database_url = sqlite:///database.db
# For production:
# database_url = postgresql://user:pass@localhost:5432/litepolis
sqlalchemy_engine_pool_size = 30
sqlalchemy_pool_max_overflow = 50
```

Or set environment variables:
```bash
export DATABASE_URL="postgresql://user:pass@localhost:5432/litepolis"
```

## Models

### ParticiapiUser (participants table)

| Column | Type | Description |
|--------|------|-------------|
| pid | INTEGER | Participant ID (primary key) |
| uid | INTEGER | User ID |
| zid | INTEGER | Conversation ID |
| vote_count | INTEGER | Number of votes cast |
| last_interaction | INTEGER | Last activity timestamp (ms) |
| subscribed | BOOLEAN | Email subscription status |
| last_notified | INTEGER | Last notification timestamp (ms) |
| nsli | INTEGER | Not-since-last-interaction flag |
| mod | INTEGER | Moderation status |
| created | DATETIME | Creation timestamp |

### ParticipantExtended (participants_extended table)

| Column | Type | Description |
|--------|------|-------------|
| uid | INTEGER | User ID |
| zid | INTEGER | Conversation ID |
| referrer | VARCHAR | HTTP referrer |
| parent_url | VARCHAR | Parent page URL |
| created | DATETIME | Creation timestamp |
| modified | DATETIME | Last modified timestamp |
| subscribe_email | BOOLEAN | Email subscription |
| show_translation_activated | BOOLEAN | Translation feature |
| permanent_cookie | VARCHAR | Persistent cookie |
| origin | VARCHAR | Origin header |

## Quick Start

1. Install all ParticiAPI modules:
```bash
litepolis-cli deploy add-deps litepolis-database-particiapi
litepolis-cli deploy add-deps litepolis-router-particiapi
litepolis-cli deploy add-deps litepolis-ui-particiapp
litepolis-cli deploy sync-deps
```

2. Start LitePolis server:
```bash
litepolis-cli deploy serve
```

## Usage

```python
from litepolis_database_particiapi import DatabaseActor

# Get or create participant
participant = DatabaseActor.get_or_create_participant(zid=1, uid=1)

# Record vote
vote = DatabaseActor.do_vote(zid=1, pid=1, tid=1, vote=1)

# Get statements for conversation
statements = DatabaseActor.get_statements(zid=1)
```

## DatabaseActor Methods

| Method | Description |
|--------|-------------|
| `get_or_create_participant(zid, uid)` | Get or create participant for conversation |
| `do_vote(zid, pid, tid, vote)` | Record a vote |
| `get_statements(zid)` | Get all statements for conversation |
| `get_conversation(zid)` | Get conversation details |
| `create_statement(zid, pid, text)` | Create new statement |

## Development Testing

```bash
pip install -e .
pytest tests/
```

## Related Modules

- [LitePolis-router-particiapi](../LitePolis-router-particiapi) - ParticiAPI router
- [LitePolis-ui-particiapp](../LitePolis-ui-particiapp) - ParticiApp frontend

## License

MIT License
