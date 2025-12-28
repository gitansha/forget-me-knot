# 📚 API Documentation

## Overview

The Plant Watering Tracker Bot uses the Telegram Bot API and provides a webhook endpoint for receiving updates. This document describes the technical architecture and API endpoints.

---

## Table of Contents

- [Architecture](#architecture)
- [Webhook Endpoint](#webhook-endpoint)
- [Redis Data Layer](#redis-data-layer)
- [Bot Commands API](#bot-commands-api)
- [Automated Scripts](#automated-scripts)
- [Error Handling](#error-handling)

---

## Architecture

```
┌─────────────┐         ┌──────────────┐         ┌─────────────┐
│   Telegram  │────────▶│    Vercel    │────────▶│    Redis    │
│     Bot     │◀────────│   Webhook    │◀────────│   Database  │
└─────────────┘         └──────────────┘         └─────────────┘
                              │
                              │
                        ┌─────▼──────┐
                        │   GitHub   │
                        │   Actions  │
                        └────────────┘
```

### Components

1. **Telegram Bot API**: Receives user messages and sends responses
2. **Vercel Serverless Function**: Processes webhook requests
3. **Redis Database**: Stores user and plant data
4. **GitHub Actions**: Automated reminders and cleanup

---

## Webhook Endpoint

### Base URL
```
https://your-app.vercel.app/webhook
```

### POST /webhook

Receives updates from Telegram Bot API.

**Request Headers:**
```
Content-Type: application/json
```

**Request Body:**
```json
{
  "update_id": 123456789,
  "message": {
    "message_id": 123,
    "from": {
      "id": 987654321,
      "is_bot": false,
      "first_name": "John",
      "username": "john_doe"
    },
    "chat": {
      "id": 987654321,
      "first_name": "John",
      "username": "john_doe",
      "type": "private"
    },
    "date": 1701360000,
    "text": "/start"
  }
}
```

**Response:**
```json
{
  "ok": true
}
```

**Status Codes:**
- `200`: Update processed successfully
- `500`: Server error

---

### GET /webhook

Health check endpoint.

**Response:**
```
🌱 Plant Bot is running!
```

**Status Code:**
- `200`: Service is healthy

---

## Redis Data Layer

### Connection

```python
import redis.asyncio as redis

client = redis.from_url(
    REDIS_URL,
    encoding="utf-8",
    decode_responses=True
)
```

### Data Models

#### Chat IDs List

**Key:** `plant_bot:chat_ids`

**Type:** JSON Array

**Structure:**
```json
[123456789, 987654321, 456789123]
```

**Operations:**
```python
# Get all chat IDs
chat_ids = await client.get("plant_bot:chat_ids")
chat_ids_list = json.loads(chat_ids) if chat_ids else []

# Add chat ID
chat_ids_list.append(new_chat_id)
await client.set("plant_bot:chat_ids", json.dumps(chat_ids_list))
```

---

#### Reminders Status

**Key:** `plant_bot:reminders_enabled`

**Type:** String

**Values:** `"true"` or `"false"`

**Operations:**
```python
# Check if enabled
enabled = await client.get("plant_bot:reminders_enabled")
is_enabled = enabled != "false" if enabled else True

# Enable/disable
await client.set("plant_bot:reminders_enabled", "true")
await client.set("plant_bot:reminders_enabled", "false")
```

---

#### Plant Data

**Key Pattern:** `plant_bot:user:{user_id}`

**Type:** JSON Object

**Structure:**
```json
{
  "username": "John",
  "plant_name": "Cactus Carl",
  "last_watered": "2024-11-30T14:30:00.000000",
  "watered_by": "John",
  "created_at": "2024-11-01T10:00:00.000000"
}
```

**Field Descriptions:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `username` | string | Yes | User's display name |
| `plant_name` | string | Yes | Custom plant name |
| `last_watered` | ISO datetime | No | Last watering timestamp |
| `watered_by` | string | No | Who watered the plant |
| `created_at` | ISO datetime | Yes | Plant creation timestamp |

**Operations:**

```python
# Get plant data
key = f"plant_bot:user:{user_id}"
plant_json = await client.get(key)
plant = json.loads(plant_json) if plant_json else None

# Save plant data
await client.set(key, json.dumps(plant_data))

# Get all plants
keys = await client.keys("plant_bot:user:*")
plants = {}
for key in keys:
    plant_json = await client.get(key)
    if plant_json:
        user_id = key.replace("plant_bot:user:", "")
        plants[user_id] = json.loads(plant_json)
```

---

## Bot Commands API

### RedisDataManager Class

Manages all Redis operations.

#### Methods

##### `get_chat_ids()`
```python
async def get_chat_ids() -> List[int]
```
Returns list of all registered chat IDs.

**Returns:**
- `List[int]`: List of chat IDs
- `[]`: Empty list if none found or error

---

##### `add_chat_id(chat_id)`
```python
async def add_chat_id(chat_id: int) -> bool
```
Adds a chat ID to the registered list.

**Parameters:**
- `chat_id` (int): Telegram chat ID

**Returns:**
- `True`: Successfully added
- `False`: Error occurred

---

##### `get_reminders_enabled()`
```python
async def get_reminders_enabled() -> bool
```
Checks if reminders are enabled.

**Returns:**
- `True`: Reminders enabled
- `False`: Reminders disabled

---

##### `set_reminders_enabled(enabled)`
```python
async def set_reminders_enabled(enabled: bool) -> bool
```
Enable or disable reminders.

**Parameters:**
- `enabled` (bool): True to enable, False to disable

**Returns:**
- `True`: Successfully updated
- `False`: Error occurred

---

##### `get_plant(user_id)`
```python
async def get_plant(user_id: int) -> Optional[Dict]
```
Gets plant data for a specific user.

**Parameters:**
- `user_id` (int): Telegram user ID

**Returns:**
- `Dict`: Plant data object
- `None`: No plant found or error

---

##### `save_plant(user_id, plant_data)`
```python
async def save_plant(user_id: int, plant_data: Dict) -> bool
```
Saves plant data for a user.

**Parameters:**
- `user_id` (int): Telegram user ID
- `plant_data` (Dict): Plant data object

**Returns:**
- `True`: Successfully saved
- `False`: Error occurred

---

##### `get_all_plants()`
```python
async def get_all_plants() -> Dict[str, Dict]
```
Gets all plants from database.

**Returns:**
- `Dict[str, Dict]`: Dictionary mapping user_id to plant data
- `{}`: Empty dict if none found or error

---

### PlantBotHandlers Class

Handles all bot commands.

#### Command Handlers

##### `/start`
```python
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE)
```
Registers user and creates initial plant.

**Behavior:**
1. Registers chat ID
2. Checks if user has existing plant
3. Creates new plant if needed
4. Sends welcome message

---

##### `/watered`
```python
async def watered(update: Update, context: ContextTypes.DEFAULT_TYPE)
```
Marks plant as watered.

**Behavior:**
1. Gets or creates plant for user
2. Updates `last_watered` timestamp
3. Sets `watered_by` to current user
4. Sends confirmation message

---

##### `/mystatus`
```python
async def my_status(update: Update, context: ContextTypes.DEFAULT_TYPE)
```
Shows current user's plant status.

**Behavior:**
1. Gets user's plant
2. Calculates days since last watering
3. Calculates next watering date
4. Sends status message

---

##### `/status`
```python
async def status(update: Update, context: ContextTypes.DEFAULT_TYPE)
```
Shows all plants' status.

**Behavior:**
1. Gets all plants from database
2. Formats status for each plant
3. Shows which plants need watering
4. Sends combined status message

---

##### `/setplant [name]`
```python
async def set_plant_name(update: Update, context: ContextTypes.DEFAULT_TYPE)
```
Sets custom plant name.

**Parameters:**
- `name` (string): New plant name (from command args)

**Behavior:**
1. Gets or creates plant
2. Updates `plant_name` if name provided
3. Shows current name if no name provided
4. Sends confirmation message

---

##### `/help`
```python
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE)
```
Shows help message with all commands.

---

##### `/enable`
```python
async def enable_reminders(update: Update, context: ContextTypes.DEFAULT_TYPE)
```
Enables watering reminders for all users.

---

##### `/disable`
```python
async def disable_reminders(update: Update, context: ContextTypes.DEFAULT_TYPE)
```
Disables watering reminders for all users.

---

## Automated Scripts

### Send Reminders Script

**File:** `scripts/send_reminders.py`

**Schedule:** 8 AM & 8 PM UTC daily (via GitHub Actions)

**Function:**
```python
async def send_reminders()
```

**Behavior:**
1. Checks if reminders are enabled
2. Gets all plants from database
3. Identifies plants needing water (3+ days since last watering)
4. Builds reminder message with random greeting
5. Sends message to all registered chat IDs

**Message Format:**
```
💧 Time to water your plants!

🌱 Cactus Carl (John) - 2 days overdue!
🌱 Fern Fernando (Sarah) - Never watered!

Use /watered when you've watered your plant! 🌿
```

---

### Cleanup Script

**File:** `scripts/cleanup_old_data.py`

**Schedule:** Every Sunday at 2 AM UTC (via GitHub Actions)

**Function:**
```python
async def cleanup_old_data()
```

**Behavior:**
1. Sets cutoff date (7 days ago)
2. Gets all plant keys from database
3. For each plant:
   - If never watered: Check creation date
   - If watered: Check last watered date
   - Delete if older than cutoff
4. Logs summary of deleted/kept records

**Deletion Criteria:**
- Never watered + created > 7 days ago
- Last watered > 7 days ago

---

## Error Handling

### Redis Connection Errors

```python
try:
    client = await get_redis_client()
    # Perform operations
except redis.ConnectionError as e:
    logger.error(f"Redis connection failed: {e}")
    return default_value
finally:
    if client:
        await client.close()
```

### Telegram API Errors

```python
try:
    await update.message.reply_text(message)
except telegram.error.TelegramError as e:
    logger.error(f"Failed to send message: {e}")
```

### JSON Parsing Errors

```python
try:
    data = json.loads(json_string)
except json.JSONDecodeError as e:
    logger.error(f"Invalid JSON: {e}")
    return None
```

### Webhook Processing Errors

```python
try:
    await handle_update(update_data)
except Exception as e:
    logger.error(f"Error processing update: {e}", exc_info=True)
    return {"statusCode": 500, "body": str(e)}
```

---

## Rate Limits

### Telegram Bot API

- **Messages:** 30 messages per second
- **Group messages:** 20 messages per minute per group
- **Private messages:** No specific limit

### Redis (Upstash Free Tier)

- **Requests:** 10,000 commands/day
- **Storage:** 256 MB
- **Bandwidth:** 256 MB/day

### Vercel (Hobby Plan)

- **Function duration:** 10 seconds max
- **Deployments:** 100/day
- **Bandwidth:** 100 GB/month

---

## Security Considerations

### Environment Variables

Never expose these in code:
- `TELEGRAM_BOT_TOKEN`
- `REDIS_URL`

Always use environment variables or secrets.

### Webhook Security

Optional: Verify webhook requests from Telegram

```python
import hmac
import hashlib

def verify_telegram_webhook(request_data, secret_token):
    """Verify webhook request is from Telegram"""
    # Implementation depends on Telegram's verification method
    pass
```

### Input Validation

Always validate user input:

```python
def sanitize_plant_name(name: str) -> str:
    """Sanitize plant name input"""
    # Remove special characters, limit length
    cleaned = re.sub(r'[^\w\s-]', '', name)
    return cleaned[:50]  # Max 50 characters
```

---

## Monitoring

### Logging Levels

```python
logging.DEBUG    # Detailed debugging info
logging.INFO     # General information
logging.WARNING  # Warning messages
logging.ERROR    # Error messages
logging.CRITICAL # Critical errors
```

### Key Metrics to Monitor

- Webhook response times
- Redis connection success rate
- Command execution success rate
- Error frequency
- Active user count
- Message volume

### Vercel Logs

```bash
# View logs
vercel logs

# Follow logs in real-time
vercel logs --follow

# Filter by date
vercel logs --since=1h
```

---

## Performance Optimization

### Redis Connection Pooling

```python
# Use connection pooling for better performance
pool = redis.ConnectionPool.from_url(REDIS_URL)
client = redis.Redis(connection_pool=pool)
```

### Async Operations

All I/O operations use `async/await` for non-blocking execution:

```python
# Multiple concurrent operations
results = await asyncio.gather(
    client.get(key1),
    client.get(key2),
    client.get(key3)
)
```

### Caching

Consider caching frequently accessed data:

```python
# Cache reminder status for 5 minutes
cache = {}
cache_ttl = 300  # seconds

async def get_reminders_enabled_cached():
    if 'reminders' in cache:
        if time.time() - cache['reminders']['time'] < cache_ttl:
            return cache['reminders']['value']
    
    value = await get_reminders_enabled()
    cache['reminders'] = {'value': value, 'time': time.time()}
    return value
```

---

## Testing

### Unit Tests

```python
import pytest
from unittest.mock import AsyncMock, MagicMock

@pytest.mark.asyncio
async def test_add_chat_id():
    dm = RedisDataManager()
    dm._get_client = AsyncMock()
    
    result = await dm.add_chat_id(123456)
    assert result == True
```

### Integration Tests

```python
@pytest.mark.asyncio
async def test_full_workflow():
    # Test complete user flow
    # 1. Start command
    # 2. Water plant
    # 3. Check status
    pass
```

### Load Testing

Use tools like `locust` to test webhook performance:

```python
from locust import HttpUser, task

class BotUser(HttpUser):
    @task
    def send_message(self):
        self.client.post("/webhook", json={
            "update_id": 123,
            "message": {"text": "/start"}
        })
```

---

## API Versioning

Current version: **v1.0.0**

Future versions will maintain backwards compatibility.

### Version History

- **v1.0.0** (2024-11-30): Initial release
  - Basic plant tracking
  - Watering reminders
  - Status commands
  - Auto cleanup

---

## Support

For technical issues or questions:

- 📧 Email: support@plantbot.com
- 🐛 Issues: GitHub Issues
- 📖 Docs: This document

---

**Last Updated:** 2024-11-30
