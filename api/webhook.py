import os
import json
import logging
from datetime import datetime, timedelta
from telegram import Update, Bot
from telegram.ext import Application, CommandHandler, ContextTypes
import asyncio
import redis.asyncio as redis
from http.server import BaseHTTPRequestHandler

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
REDIS_URL = os.getenv("REDIS_URL")

# Log startup info
logger.info(f"🚀 Bot starting up...")
logger.info(f"📝 BOT_TOKEN exists: {bool(BOT_TOKEN)}")
logger.info(f"📝 REDIS_URL exists: {bool(REDIS_URL)}")

# Redis Keys
CHAT_IDS_KEY = "plant_bot:chat_ids"
REMINDERS_KEY = "plant_bot:reminders_enabled"
PLANT_PREFIX = "plant_bot:user:"


class RedisDataManager:
    """Manages data in Redis"""

    def __init__(self):
        self.redis_url = REDIS_URL

    async def _get_client(self):
        """Get Redis client"""
        return redis.from_url(self.redis_url, encoding="utf-8", decode_responses=True)

    async def get_chat_ids(self):
        """Get all registered chat IDs"""
        client = None
        try:
            client = await self._get_client()
            chat_ids = await client.get(CHAT_IDS_KEY)
            return json.loads(chat_ids) if chat_ids else []
        except Exception as e:
            logger.error(f"Error getting chat IDs: {e}")
            return []
        finally:
            if client:
                await client.close()

    async def add_chat_id(self, chat_id):
        """Add a chat ID to the list"""
        client = None
        try:
            client = await self._get_client()
            chat_ids = await self.get_chat_ids()
            if chat_id not in chat_ids:
                chat_ids.append(chat_id)
                await client.set(CHAT_IDS_KEY, json.dumps(chat_ids))
            return True
        except Exception as e:
            logger.error(f"Error adding chat ID: {e}")
            return False
        finally:
            if client:
                await client.close()

    async def get_reminders_enabled(self):
        """Check if reminders are enabled"""
        client = None
        try:
            client = await self._get_client()
            enabled = await client.get(REMINDERS_KEY)
            return enabled != "false" if enabled else True
        except Exception as e:
            logger.error(f"Error getting reminders status: {e}")
            return True
        finally:
            if client:
                await client.close()

    async def set_reminders_enabled(self, enabled):
        """Enable/disable reminders"""
        client = None
        try:
            client = await self._get_client()
            await client.set(REMINDERS_KEY, "true" if enabled else "false")
            return True
        except Exception as e:
            logger.error(f"Error setting reminders: {e}")
            return False
        finally:
            if client:
                await client.close()

    async def get_plant(self, user_id):
        """Get plant data for a user"""
        client = None
        try:
            client = await self._get_client()
            key = f"{PLANT_PREFIX}{user_id}"
            plant_data = await client.get(key)
            return json.loads(plant_data) if plant_data else None
        except Exception as e:
            logger.error(f"Error getting plant for {user_id}: {e}")
            return None
        finally:
            if client:
                await client.close()

    async def save_plant(self, user_id, plant_data):
        """Save plant data for a user"""
        client = None
        try:
            client = await self._get_client()
            key = f"{PLANT_PREFIX}{user_id}"
            await client.set(key, json.dumps(plant_data))
            return True
        except Exception as e:
            logger.error(f"Error saving plant for {user_id}: {e}")
            return False
        finally:
            if client:
                await client.close()

    async def get_all_plants(self):
        """Get all plants (for status command)"""
        client = None
        try:
            client = await self._get_client()
            keys = await client.keys(f"{PLANT_PREFIX}*")
            plants = {}

            for key in keys:
                plant_data = await client.get(key)
                if plant_data:
                    user_id = key.replace(PLANT_PREFIX, "")
                    plants[user_id] = json.loads(plant_data)

            return plants
        except Exception as e:
            logger.error(f"Error getting all plants: {e}")
            return {}
        finally:
            if client:
                await client.close()


class PlantBotHandlers:
    def __init__(self, dm):
        self.dm = dm

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        logger.info("🌱 START command handler called!")

        chat_id = update.effective_chat.id
        user_id = update.effective_user.id
        username = (
            update.effective_user.first_name
            or update.effective_user.username
            or "Unknown"
        )

        logger.info(f"👤 User: {username} (ID: {user_id})")
        logger.info(f"💬 Chat ID: {chat_id}")

        # Register chat
        await self.dm.add_chat_id(chat_id)
        logger.info(f"✅ Chat ID registered")

        # Check if user already has a plant
        plant = await self.dm.get_plant(user_id)

        if not plant:
            logger.info(f"🆕 Creating new plant for user")
            plant = {
                "username": username,
                "plant_name": f"{username}'s Plant",
                "last_watered": None,
                "watered_by": None,
                "created_at": datetime.now().isoformat(),
            }
            await self.dm.save_plant(user_id, plant)
        else:
            logger.info(f"🌱 User already has plant: {plant['plant_name']}")

        msg = f"""
🌱 Welcome {username}! Plant Bot activated! 🌱

Your plant: **{plant["plant_name"]}**

Commands:
- /watered - Mark your plant as watered
- /status - Check all plants
- /mystatus - Check your plant status
- /setplant [name] - Name your plant
- /help - Show all commands

Track your plants! 🌿
Note: Data older than 7 days is automatically cleaned up.
        """

        logger.info(f"📤 Sending reply message...")
        await update.message.reply_text(msg)
        logger.info(f"✅ Reply sent successfully!")

    async def watered(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        logger.info("💧 WATERED command handler called!")

        user_id = update.effective_user.id
        username = (
            update.effective_user.first_name
            or update.effective_user.username
            or "Someone"
        )

        plant = await self.dm.get_plant(user_id)

        if not plant:
            plant = {
                "username": username,
                "plant_name": f"{username}'s Plant",
                "last_watered": None,
                "watered_by": None,
                "created_at": datetime.now().isoformat(),
            }

        plant["last_watered"] = datetime.now().isoformat()
        plant["watered_by"] = username
        plant["username"] = username

        await self.dm.save_plant(user_id, plant)

        msg = f"✅ {username} watered {plant['plant_name']}! 🌱\n"
        msg += f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
        msg += "🗓️ Next watering: 3 days"

        await update.message.reply_text(msg)
        logger.info(f"✅ Watered reply sent!")

    async def my_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        logger.info("📊 MYSTATUS command handler called!")

        user_id = update.effective_user.id
        plant = await self.dm.get_plant(user_id)

        if not plant:
            await update.message.reply_text(
                "🌱 You haven't registered yet! Use /start first."
            )
            return

        if not plant["last_watered"]:
            await update.message.reply_text(
                f"🌱 {plant['plant_name']} has never been watered yet!"
            )
            return

        last_watered = datetime.fromisoformat(plant["last_watered"])
        days_since = (datetime.now() - last_watered).days
        next_watering = last_watered + timedelta(days=3)

        msg = f"📊 {plant['plant_name']} Status:\n\n"
        msg += f"💧 Last watered: {last_watered.strftime('%Y-%m-%d %H:%M')}\n"
        msg += f"👤 Watered by: {plant['watered_by']}\n"
        msg += f"⏰ Days since: {days_since}\n"
        msg += f"📅 Next watering: {next_watering.strftime('%Y-%m-%d')}\n\n"

        if days_since >= 3:
            msg += "⚠️ Needs watering NOW!"
        else:
            days_left = 3 - days_since
            msg += f"✅ Good for {days_left} more day(s)"

        await update.message.reply_text(msg)

    async def status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        logger.info("📋 STATUS command handler called!")

        plants = await self.dm.get_all_plants()

        if not plants:
            await update.message.reply_text(
                "🌱 No plants registered yet! Everyone should use /start first."
            )
            return

        msg = "🌿 All Plants Status:\n\n"

        for user_id, plant in plants.items():
            plant_name = plant["plant_name"]
            username = plant["username"]

            msg += f"🌱 {plant_name} ({username})\n"

            if not plant["last_watered"]:
                msg += "   ❌ Never watered\n\n"
                continue

            last_watered = datetime.fromisoformat(plant["last_watered"])
            days_since = (datetime.now() - last_watered).days

            msg += f"   💧 Last: {last_watered.strftime('%m-%d %H:%M')}\n"
            msg += f"   ⏰ {days_since} days ago\n"

            if days_since >= 3:
                msg += "   ⚠️ Needs water!\n\n"
            else:
                days_left = 3 - days_since
                msg += f"   ✅ Good for {days_left} day(s)\n\n"

        await update.message.reply_text(msg)

    async def set_plant_name(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        logger.info("✏️ SETPLANT command handler called!")

        user_id = update.effective_user.id
        username = (
            update.effective_user.first_name
            or update.effective_user.username
            or "Unknown"
        )

        plant = await self.dm.get_plant(user_id)

        if not plant:
            plant = {
                "username": username,
                "plant_name": f"{username}'s Plant",
                "last_watered": None,
                "watered_by": None,
                "created_at": datetime.now().isoformat(),
            }

        if context.args:
            new_name = " ".join(context.args)
            plant["plant_name"] = new_name
            await self.dm.save_plant(user_id, plant)
            await update.message.reply_text(f"🌱 Your plant is now named: {new_name}")
        else:
            current_name = plant["plant_name"]
            await update.message.reply_text(
                f"🌱 Current plant name: {current_name}\n\n"
                f"To change it, use: /setplant New Plant Name"
            )

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        logger.info("❓ HELP command handler called!")

        help_text = """
🌱 **Plant Bot Commands:**

**Plant Care:**
- /watered - Mark your plant as watered
- /mystatus - Check your plant status
- /status - Check everyone's plants

**Setup:**
- /start - Register yourself and your plant
- /setplant [name] - Give your plant a custom name

**Settings:**
- /enable - Turn on reminders
- /disable - Turn off reminders
- /help - Show this help message

Each person tracks their own plant! 🌿
Data older than 7 days is automatically cleaned up.
        """
        await update.message.reply_text(help_text)

    async def enable_reminders(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        logger.info("🔔 ENABLE command handler called!")
        await self.dm.set_reminders_enabled(True)
        await update.message.reply_text("✅ Watering reminders enabled for everyone!")

    async def disable_reminders(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        logger.info("🔕 DISABLE command handler called!")
        await self.dm.set_reminders_enabled(False)
        await update.message.reply_text("❌ Watering reminders disabled!")


async def handle_update(update_data):
    """Process incoming webhook update"""
    try:
        logger.info("=" * 50)
        logger.info(f"📨 FULL UPDATE DATA:")
        logger.info(json.dumps(update_data, indent=2))
        logger.info("=" * 50)

        # Check if it's a message
        if "message" in update_data:
            message = update_data["message"]
            logger.info(f"📝 Message text: {message.get('text', 'NO TEXT')}")
            logger.info(
                f"👤 From user: {message.get('from', {}).get('first_name', 'UNKNOWN')}"
            )
            logger.info(f"💬 Chat ID: {message.get('chat', {}).get('id', 'UNKNOWN')}")

        dm = RedisDataManager()
        handlers = PlantBotHandlers(dm)

        logger.info("🔧 Building application...")
        app = Application.builder().token(BOT_TOKEN).build()

        # Add command handlers
        logger.info("➕ Adding command handlers...")
        app.add_handler(CommandHandler("start", handlers.start))
        app.add_handler(CommandHandler("watered", handlers.watered))
        app.add_handler(CommandHandler("status", handlers.status))
        app.add_handler(CommandHandler("mystatus", handlers.my_status))
        app.add_handler(CommandHandler("setplant", handlers.set_plant_name))
        app.add_handler(CommandHandler("help", handlers.help_command))
        app.add_handler(CommandHandler("enable", handlers.enable_reminders))
        app.add_handler(CommandHandler("disable", handlers.disable_reminders))

        logger.info("🚀 Initializing application...")
        await app.initialize()

        logger.info("⚙️ Processing update...")
        await app.process_update(Update.de_json(update_data, app.bot))

        logger.info("🛑 Shutting down application...")
        await app.shutdown()

        logger.info("✅ Update processed successfully!")
        logger.info("=" * 50)

    except Exception as e:
        logger.error("=" * 50)
        logger.error(f"❌ ERROR in handle_update: {e}", exc_info=True)
        logger.error("=" * 50)
        raise


class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        """Handle incoming webhook from Telegram"""
        try:
            content_length = int(self.headers.get("Content-Length", 0))
            post_data = self.rfile.read(content_length)
            update_data = json.loads(post_data.decode("utf-8"))

            logger.info("🌐 POST request received")

            # Process the update
            asyncio.run(handle_update(update_data))

            # Send success response
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            response = json.dumps({"ok": True})
            self.wfile.write(response.encode("utf-8"))

        except Exception as e:
            logger.error(f"❌ Error in POST handler: {e}", exc_info=True)
            self.send_response(500)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            response = json.dumps({"ok": False, "error": str(e)})
            self.wfile.write(response.encode("utf-8"))

    def do_GET(self):
        """Handle GET requests - health check"""
        logger.info("🌐 GET request received")
        self.send_response(200)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.end_headers()
        self.wfile.write("🌱 Plant Bot is running!".encode("utf-8"))
