# 🌱 Forget-me-knot :: Plant Watering Tracker Bot

A smart Telegram bot that helps you track and manage your plant watering schedule. Never forget to water your plants again! Built with Python, deployed on Vercel, and powered by Redis for data persistence.

![Plant Bot](https://img.shields.io/badge/Telegram-Bot-blue?logo=telegram)
![Python](https://img.shields.io/badge/Python-3.11-green?logo=python)
![Vercel](https://img.shields.io/badge/Deployed%20on-Vercel-black?logo=vercel)
![Redis](https://img.shields.io/badge/Database-Redis-red?logo=redis)

---

## ✨ Features

- 🌿 **Personal Plant Tracking** - Each user tracks their own plant
- 💧 **Watering Reminders** - Automated reminders via GitHub Actions (8 AM & 8 PM UTC)
- 📊 **Status Dashboard** - View all plants and their watering status
- 🏷️ **Custom Plant Names** - Give your plant a unique name
- 🔔 **Enable/Disable Reminders** - Control notification preferences
- 🧹 **Auto Cleanup** - Removes inactive data after 7 days
- ⚡ **Serverless** - Runs on Vercel with no server maintenance
- 💾 **Persistent Storage** - Data stored in Redis

---

## 📸 Screenshots

### Starting the Bot
```
🌱 Welcome John! Plant Bot activated! 🌱

Your plant: **John's Plant**

Commands:
- /watered - Mark your plant as watered
- /status - Check all plants
- /mystatus - Check your plant status
- /setplant [name] - Name your plant
- /help - Show all commands
```

### Watering Your Plant
```
✅ John watered John's Plant! 🌱
📅 2024-11-30 14:30
🗓️ Next watering: 3 days
```

### Checking Status
```
🌿 All Plants Status:

🌱 Cactus Carl (John)
   💧 Last: 11-28 10:15
   ⏰ 2 days ago
   ✅ Good for 1 day(s)

🌱 Fern Fernando (Sarah)
   💧 Last: 11-25 08:00
   ⏰ 5 days ago
   ⚠️ Needs water!
```

---

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- Telegram Account
- Vercel Account (free tier works)
- Redis Database (Upstash free tier recommended)
- GitHub Account (for automated reminders)

### 1. Create Telegram Bot

1. Open Telegram and message [@BotFather](https://t.me/botfather)
2. Send `/newbot` and follow the instructions
3. Save your bot token (looks like `123456789:ABCdefGHIjklMNOpqrsTUVwxyz`)

### 2. Set Up Redis Database

1. Sign up at [Upstash](https://upstash.com/)
2. Create a new Redis database
3. Copy the connection URL:
   ```
   redis://default:YOUR_PASSWORD@HOST:PORT
   ```

### 3. Clone and Set Up Project

```bash
# Clone the repository
git clone https://github.com/yourusername/plant-bot.git
cd plant-bot

# Create project structure
mkdir -p api scripts .github/workflows

# Install dependencies (optional, for local testing)
pip install -r requirements.txt
```

### 4. Deploy to Vercel

```bash
# Install Vercel CLI
npm install -g vercel

# Login to Vercel
vercel login

# Deploy
vercel --prod
```

### 5. Configure Environment Variables

In your Vercel Dashboard:
1. Go to **Project Settings** → **Environment Variables**
2. Add these variables:

| Variable | Value | Description |
|----------|-------|-------------|
| `TELEGRAM_BOT_TOKEN` | Your bot token | From BotFather |
| `REDIS_URL` | Your Redis URL | From Upstash |

3. **Redeploy** after adding variables:
```bash
vercel --prod
```

### 6. Set Telegram Webhook

Replace `<YOUR_BOT_TOKEN>` and `<YOUR_VERCEL_URL>` with your actual values:

```bash
# Set webhook
curl -X POST "https://api.telegram.org/bot<YOUR_BOT_TOKEN>/setWebhook?url=https://<YOUR_VERCEL_URL>/webhook"

# Verify webhook
curl "https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getWebhookInfo"
```

**Expected response:**
```json
{
  "ok": true,
  "result": {
    "url": "https://your-app.vercel.app/webhook",
    "pending_update_count": 0,
    "last_error_date": 0
  }
}
```

### 7. Configure GitHub Actions (Optional)

For automated reminders and cleanup:

1. Go to your GitHub repository → **Settings** → **Secrets and variables** → **Actions**
2. Add these secrets:
   - `TELEGRAM_BOT_TOKEN`
   - `REDIS_URL`

The workflows will automatically:
- 🔔 **Send reminders** at 8 AM & 8 PM UTC daily
- 🧹 **Clean up old data** every Sunday at 2 AM UTC

---

## 📖 Bot Commands

| Command | Description | Example |
|---------|-------------|---------|
| `/start` | Register yourself and your plant | `/start` |
| `/watered` | Mark your plant as watered | `/watered` |
| `/status` | Check all plants in the group | `/status` |
| `/mystatus` | Check your plant's status | `/mystatus` |
| `/setplant [name]` | Give your plant a custom name | `/setplant Cactus Carl` |
| `/enable` | Turn on watering reminders | `/enable` |
| `/disable` | Turn off watering reminders | `/disable` |
| `/help` | Show help message | `/help` |

---

## 🏗️ Project Structure

```
plant-bot/
├── api/
│   └── webhook.py              # Main bot logic and Vercel handler
├── scripts/
│   ├── cleanup_old_data.py     # Removes data older than 7 days
│   └── send_reminders.py       # Sends watering reminders
├── .github/
│   └── workflows/
│       ├── cleanup.yml         # Cleanup automation
│       └── reminders.yml       # Reminder automation
├── requirements.txt            # Python dependencies
├── vercel.json                 # Vercel configuration
├── plant_reminders.txt         # Fun reminder messages
├── .gitignore                  # Git ignore rules
└── README.md                   # This file
```

---

## 🔧 Configuration

### Watering Schedule

Plants need watering every **3 days** by default. To change this:

1. Edit `api/webhook.py`
2. Find the watering logic in the handlers
3. Change `days_since >= 3` to your desired number

### Reminder Times

Reminders are sent at **8 AM & 8 PM UTC**. To change:

1. Edit `.github/workflows/reminders.yml`
2. Modify the cron schedule:
   ```yaml
   schedule:
     - cron: '0 8,20 * * *'  # Hour Minute format (UTC)
   ```

[Cron expression help](https://crontab.guru/)

### Data Retention

Old data is automatically cleaned after **7 days**. To change:

1. Edit `scripts/cleanup_old_data.py`
2. Change `timedelta(days=7)` to your desired retention period

---

## 🧪 Testing

### Local Testing

```bash
# Set environment variables
export TELEGRAM_BOT_TOKEN="your-token"
export REDIS_URL="your-redis-url"

# Test Redis connection
python scripts/test_redis.py

# Test reminder script
python scripts/send_reminders.py

# Test cleanup script
python scripts/cleanup_old_data.py
```

### Production Testing

1. **Test webhook endpoint:**
   ```bash
   curl https://your-app.vercel.app/webhook
   # Should return: "🌱 Plant Bot is running!"
   ```

2. **Test bot commands:**
   - Send `/start` to your bot
   - Send `/watered`
   - Send `/status`

3. **Check logs:**
   ```bash
   vercel logs --follow
   ```

---

## 🐛 Troubleshooting

### Bot not responding

**Check webhook:**
```bash
curl "https://api.telegram.org/bot<TOKEN>/getWebhookInfo"
```

**Common issues:**
- ❌ `pending_update_count` > 0 → Webhook URL is wrong
- ❌ `last_error_message` exists → Check Vercel logs
- ❌ Wrong URL → Delete and reset webhook

**Fix:**
```bash
# Delete webhook
curl -X POST "https://api.telegram.org/bot<TOKEN>/deleteWebhook"

# Set correct webhook
curl -X POST "https://api.telegram.org/bot<TOKEN>/setWebhook?url=https://YOUR-APP.vercel.app/webhook"
```

### Redis connection errors

**Check Redis URL format:**
```
redis://default:PASSWORD@HOST:PORT
```

**Test connection:**
```python
import redis
r = redis.from_url("your-redis-url")
r.ping()  # Should return True
```

### Environment variables not working

1. Verify variables in Vercel Dashboard
2. Redeploy after adding/changing variables:
   ```bash
   vercel --prod
   ```

### GitHub Actions not running

1. Check secrets are set in GitHub repo
2. Manually trigger workflows:
   - Go to **Actions** tab
   - Select workflow
   - Click **Run workflow**

---

## 📊 Data Structure

### Redis Keys

| Key Pattern | Description | Example |
|-------------|-------------|---------|
| `plant_bot:chat_ids` | List of registered chat IDs | `[123456, 789012]` |
| `plant_bot:reminders_enabled` | Reminder status | `"true"` or `"false"` |
| `plant_bot:user:{user_id}` | Plant data for each user | See below |

### Plant Data Schema

```json
{
  "username": "John",
  "plant_name": "Cactus Carl",
  "last_watered": "2024-11-30T14:30:00",
  "watered_by": "John",
  "created_at": "2024-11-01T10:00:00"
}
```

---

## 🔐 Security

- ✅ Never commit `.env` files or tokens to Git
- ✅ Use Vercel environment variables for secrets
- ✅ Use GitHub secrets for Actions
- ✅ Rotate tokens periodically
- ✅ Keep dependencies updated

---

## 🚀 Deployment Checklist

- [ ] Create Telegram bot with BotFather
- [ ] Set up Redis database on Upstash
- [ ] Deploy to Vercel
- [ ] Add environment variables in Vercel
- [ ] Set Telegram webhook to Vercel URL
- [ ] Verify webhook with `getWebhookInfo`
- [ ] Test bot with `/start` command
- [ ] Add GitHub secrets for Actions (optional)
- [ ] Test reminders and cleanup (optional)

---

## 🤝 Contributing

Contributions are welcome! Please follow these steps:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

- [python-telegram-bot](https://github.com/python-telegram-bot/python-telegram-bot) - Telegram Bot API wrapper
- [Vercel](https://vercel.com/) - Serverless deployment platform
- [Upstash](https://upstash.com/) - Serverless Redis
- [Redis](https://redis.io/) - In-memory data store

---

## 🗺️ Roadmap

- [ ] Add photo upload for plants
- [ ] Support multiple plants per user
- [ ] Plant care tips and reminders
- [ ] Integration with plant databases
- [ ] Multi-language support

---

## ⭐ Show Your Support

If you like this project, please give it a ⭐ on GitHub!

---

**Made with 🌱 and ❤️**

*Keep your plants happy and hydrated!* 🌿
