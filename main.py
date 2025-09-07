import os
import json
import asyncio
import logging
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes, CallbackQueryHandler
import schedule
import time
from threading import Thread
from dotenv import load_dotenv
import random

# from flask import Flask


load_dotenv()  # Load variables from .env
token = os.getenv("TOKEN")

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Bot configuration
BOT_TOKEN = token  # Get from BotFather
DATA_FILE = "plant_data.json"


logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


class PlantWateringBot:
    def __init__(self):
        self.data = self.load_data()
        self.application = None

    def load_data(self):
        """Load plant data from JSON file"""
        try:
            with open(DATA_FILE, "r") as f:
                return json.load(f)
        except FileNotFoundError:
            return {
                "chat_ids": [],  # List of chat IDs for notifications
                "reminders_enabled": True,
                "plants": {},  # Dictionary to store each user's plants
                # Structure: "plants": {
                #   "user_id_123": {
                #     "username": "John",
                #     "plant_name": "My Monstera",
                #     "last_watered": "2025-09-05T10:30:00",
                #     "watered_by": "John"
                #   }
                # }
            }

    def save_data(self):
        """Save plant data to JSON file"""
        with open(DATA_FILE, "w") as f:
            json.dump(self.data, f, indent=2)

    def get_user_key(self, user_id):
        """Generate a key for storing user data"""
        return f"user_{user_id}"

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Start command - register chat and user for notifications"""
        chat_id = update.effective_chat.id
        chat_type = update.effective_chat.type
        user_id = update.effective_user.id
        username = (
            update.effective_user.first_name
            or update.effective_user.username
            or "Unknown"
        )

        # Register chat for notifications
        if chat_id not in self.data["chat_ids"]:
            self.data["chat_ids"].append(chat_id)

        # Initialize user's plant data if not exists
        user_key = self.get_user_key(user_id)
        if user_key not in self.data["plants"]:
            self.data["plants"][user_key] = {
                "username": username,
                "plant_name": f"{username}'s Plant",
                "last_watered": None,
                "watered_by": None,
            }

        self.save_data()

        if chat_type == "group" or chat_type == "supergroup":
            welcome_message = f"""
🌱 Welcome {username}! Plant Bot activated for this group! 🌱

Your plant: **{self.data["plants"][user_key]["plant_name"]}**

Commands:
• /watered - Mark your plant as watered
• /status - Check everyone's plant status
• /mystatus - Check only your plant status
• /setplant [name] - Name your plant
• /allplants - See everyone's plants
• /help - Show help
• /enable - Enable reminders
• /disable - Disable reminders

Everyone can track their own plants! 🌿
            """
        else:
            welcome_message = f"""
🌱 Welcome {username}! Your personal Plant Bot! 🌱

Your plant: {self.data["plants"][user_key]["plant_name"]}

Commands:
/watered - Mark your plant as watered
/status - Check your plant status
/setplant [name] - Name your plant
/help - Show help
/enable - Enable reminders
/disable - Disable reminders
            """
        await update.message.reply_text(welcome_message)

    async def set_plant_name(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Set a custom name for user's plant"""
        user_id = update.effective_user.id
        user_key = self.get_user_key(user_id)
        username = (
            update.effective_user.first_name
            or update.effective_user.username
            or "Unknown"
        )

        # Initialize user if not exists
        if user_key not in self.data["plants"]:
            self.data["plants"][user_key] = {
                "username": username,
                "plant_name": f"{username}'s Plant",
                "last_watered": None,
                "watered_by": None,
            }

        # Get plant name from command arguments
        if context.args:
            plant_name = " ".join(context.args)
            self.data["plants"][user_key]["plant_name"] = plant_name
            self.save_data()
            await update.message.reply_text(f"🌱 Your plant is now named: {plant_name}")
        else:
            current_name = self.data["plants"][user_key]["plant_name"]
            await update.message.reply_text(
                f"🌱 Current plant name: {current_name}\n\nTo change it, use: `/setplant New Plant Name`"
            )

    async def watered(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Mark user's plant as watered"""
        user_id = update.effective_user.id
        user_key = self.get_user_key(user_id)
        username = (
            update.effective_user.first_name
            or update.effective_user.username
            or "Someone"
        )
        chat_type = update.effective_chat.type

        # Initialize user if not exists
        if user_key not in self.data["plants"]:
            self.data["plants"][user_key] = {
                "username": username,
                "plant_name": f"{username}'s Plant",
                "last_watered": None,
                "watered_by": None,
            }

        # Update watering data
        self.data["plants"][user_key]["last_watered"] = datetime.now().isoformat()
        self.data["plants"][user_key]["watered_by"] = username
        self.save_data()

        plant_name = self.data["plants"][user_key]["plant_name"]

        if chat_type == "group" or chat_type == "supergroup":
            message = f"✅ {username} watered {plant_name}! 🌱\n"
            message += f"📅 {datetime.now().strftime('%Y-%m-%d')}\n"
            message += "🗓️ Next watering in 3 days"
        else:
            message = f"✅ {plant_name} is thriving ! 🌱\n"
            message += f"📅 {datetime.now().strftime('%Y-%m-%d')}\n"
            message += "🗓️ Next watering in 3 days"

        await update.message.reply_text(message)

    async def my_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Check only the current user's plant status"""
        user_id = update.effective_user.id
        user_key = self.get_user_key(user_id)
        username = (
            update.effective_user.first_name or update.effective_user.username or "You"
        )

        if user_key not in self.data["plants"]:
            await update.message.reply_text(
                "🌱 You haven't registered yet! Use /start first."
            )
            return

        plant_data = self.data["plants"][user_key]
        plant_name = plant_data["plant_name"]

        if not plant_data["last_watered"]:
            await update.message.reply_text(
                f"🌱 {plant_name} has never been watered (or data was reset)"
            )
            return

        last_watered = datetime.fromisoformat(plant_data["last_watered"])
        days_since = (datetime.now() - last_watered).days
        next_watering = last_watered + timedelta(days=3)

        status_message = f"📊 {plant_name} Status:\n\n"
        status_message += f"💧 Last watered: {last_watered.strftime('%Y-%m-%d')}\n"
        status_message += f"👤 Watered by: {plant_data['watered_by']}\n"
        status_message += f"⏰ Days since watered: {days_since}\n"
        status_message += f"📅 Next watering: {next_watering.strftime('%Y-%m-%d')}\n"

        if days_since >= 3:
            status_message += "⚠️ Needs watering!"
        else:
            days_left = 3 - days_since
            status_message += f"✅ Good for {days_left} more day(s)"

        await update.message.reply_text(status_message)

    async def status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Check all plants status in the chat"""
        if not self.data["plants"]:
            await update.message.reply_text(
                "🌱 No plants registered yet! Everyone should use /start first."
            )
            return

        status_message = "🌿 All Plants Status:\n\n"

        for user_key, plant_data in self.data["plants"].items():
            plant_name = plant_data["plant_name"]
            username = plant_data["username"]

            if not plant_data["last_watered"]:
                status_message += f"🌱 {plant_name} ({username})\n"
                status_message += "   ❓ Never watered\n\n"
                continue

            last_watered = datetime.fromisoformat(plant_data["last_watered"])
            days_since = (datetime.now() - last_watered).days

            status_message += f"🌱 {plant_name} ({username})\n"
            status_message += f"   💧 Last: {last_watered.strftime('%m-%d %H:%M')}\n"
            status_message += f"   ⏰ {days_since} days ago\n"

            if days_since >= 3:
                status_message += "   ⚠️ Needs water!\n\n"
            else:
                days_left = 3 - days_since
                status_message += f"   ✅ Good for {days_left} day(s)\n\n"

        await update.message.reply_text(status_message)

    async def all_plants(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show all registered plants"""
        if not self.data["plants"]:
            await update.message.reply_text("🌱 No plants registered yet!")
            return

        message = "🌿 Registered Plants:\n\n"

        for user_key, plant_data in self.data["plants"].items():
            plant_name = plant_data["plant_name"]
            username = plant_data["username"]
            message += f"🌱 {plant_name} - owned by {username}\n"

        await update.message.reply_text(message)

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show help message"""
        chat_type = update.effective_chat.type

        if chat_type == "group" or chat_type == "supergroup":
            help_text = """
🌱 **Plant Bot Commands:**

**Plant Care:**
• /watered - Mark YOUR plant as watered ✅
• /mystatus - Check your plant status 📊
• /status - Check everyone's plants 🌿
• /allplants - List all registered plants 📝

**Setup:**
• /start - Register yourself and your plant 🚀
• /setplant [name] - Give your plant a name 🏷️

**Settings:**
• /enable - Turn on reminders 🔔
• /disable - Turn off reminders 🔕
• /help - Show this help 💡

Each person tracks their own plant!. 💬
            """
        else:
            help_text = """
🌱 **Personal Plant Bot Commands:**

• /start - Register for notifications
• /watered - Mark your plant as watered
• /mystatus - Check your plant status
• /setplant [name] - Name your plant
• /enable - Enable reminders
• /disable - Disable reminders
• /help - Show this help

Perfect for tracking your personal plant care! 🌿
            """
        await update.message.reply_text(help_text)

    async def enable_reminders(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        """Enable watering reminders"""
        self.data["reminders_enabled"] = True
        self.save_data()
        await update.message.reply_text("✅ Watering reminders enabled for everyone!")

    async def disable_reminders(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        """Disable watering reminders"""
        self.data["reminders_enabled"] = False
        self.save_data()
        await update.message.reply_text("❌ Watering reminders disabled!")

    async def send_reminder_notifications(self):
        """Send reminder notifications to all registered chats"""
        if not self.data["reminders_enabled"] or not self.data["chat_ids"]:
            return

        plants_needing_water = []

        for user_key, plant_data in self.data["plants"].items():
            plant_name = plant_data["plant_name"]
            username = plant_data["username"]

            if not plant_data["last_watered"]:
                plants_needing_water.append(
                    f"🌱 {plant_name} ({username}) - Never watered!"
                )
            else:
                last_watered = datetime.fromisoformat(plant_data["last_watered"])
                days_since = (datetime.now() - last_watered).days

                if days_since >= 3:
                    days_overdue = days_since - 3
                    if days_overdue == 0:
                        plants_needing_water.append(
                            f"🌱 {plant_name} ({username}) - Due today!"
                        )
                    else:
                        plants_needing_water.append(
                            f"🌱 {plant_name} ({username}) - {days_overdue} days overdue!"
                        )

        if not plants_needing_water:
            return  # No plants need watering

        with open("plant_reminders.txt", "r") as file:
            lines = file.readlines()

        # Get a random line number
        reminder = lines[random.randint(0, len(lines) - 1)].strip()
        message = f" {reminder}\n\n"
        message += "\n".join(plants_needing_water)
        message += "\n\nUse /watered when you've watered your plant! 🌿"

        # Send to all registered chats
        for chat_id in self.data["chat_ids"]:
            try:
                await self.application.bot.send_message(chat_id=chat_id, text=message)
            except Exception as e:
                logger.error(f"Failed to send reminder to {chat_id}: {e}")

    def check_reminders(self):
        """Check if reminders should be sent (runs in background)"""
        if not self.data["reminders_enabled"] or not self.data["chat_ids"]:
            return

        # Check if any plant needs watering
        needs_reminder = False
        for user_key, plant_data in self.data["plants"].items():
            if not plant_data["last_watered"]:
                needs_reminder = True
                break
            else:
                last_watered = datetime.fromisoformat(plant_data["last_watered"])
                days_since = (datetime.now() - last_watered).days
                if days_since >= 3:
                    needs_reminder = True
                    break

        if needs_reminder and self.application:
            # # Schedule the async function to run
            # asyncio.create_task(self.send_reminder_notifications())
            # Create and run a new event loop for this thread
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            # Run the coroutine
            loop.run_until_complete(self.send_reminder_notifications())
            loop.close()

    def run_scheduler(self):
        """Run the scheduler in a separate thread"""
        schedule.every(12).hours.do(self.check_reminders)  # Check twice daily

        while True:
            schedule.run_pending()
            time.sleep(3600)  # Sleep for 1 hour

    def run(self):
        """Run the bot"""
        # Create application
        self.application = Application.builder().token(BOT_TOKEN).build()

        # Add handlers
        self.application.add_handler(CommandHandler("start", self.start))
        self.application.add_handler(CommandHandler("watered", self.watered))
        self.application.add_handler(CommandHandler("status", self.status))
        self.application.add_handler(CommandHandler("mystatus", self.my_status))
        self.application.add_handler(CommandHandler("setplant", self.set_plant_name))
        self.application.add_handler(CommandHandler("allplants", self.all_plants))
        self.application.add_handler(CommandHandler("help", self.help_command))
        self.application.add_handler(CommandHandler("enable", self.enable_reminders))
        self.application.add_handler(CommandHandler("disable", self.disable_reminders))

        # Start scheduler in background thread
        scheduler_thread = Thread(target=self.run_scheduler, daemon=True)
        scheduler_thread.start()

        # Run the bot
        self.application.run_polling()


if __name__ == "__main__":
    bot = PlantWateringBot()
    bot.run()
    print(f"Reminders enabled: {bot.data['reminders_enabled']}")
    print(f"Registered chat IDs: {bot.data['chat_ids']}")


# class PlantWateringBot:
#     def __init__(self):
#         self.data = self.load_data()
#         self.application = None

#     def load_data(self):
#         """Load plant data from JSON file"""
#         try:
#             with open(DATA_FILE, "r") as f:
#                 return json.load(f)
#         except FileNotFoundError:
#             return {
#                 "chat_ids": [],  # List of chat IDs for notifications
#                 "reminders_enabled": True,
#                 "plants": {},  # Dictionary to store each user's plants
#                 # Structure: "plants": {
#                 #   "user_id_123": {
#                 #     "username": "John",
#                 #     "plant_name": "My Monstera",
#                 #     "last_watered": "2025-09-05T10:30:00",
#                 #     "watered_by": "John"
#                 #   }
#                 # }
#             }

#     def save_data(self):
#         """Save plant data to JSON file"""
#         with open(DATA_FILE, "w") as f:
#             json.dump(self.data, f, indent=2)

#     def get_user_key(self, user_id):
#         """Generate a key for storing user data"""
#         return f"user_{user_id}"

#     async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
#         """Start command - register chat and user for notifications"""
#         chat_id = update.effective_chat.id
#         chat_type = update.effective_chat.type
#         user_id = update.effective_user.id
#         username = (
#             update.effective_user.first_name
#             or update.effective_user.username
#             or "Unknown"
#         )

#         # Register chat for notifications
#         if chat_id not in self.data["chat_ids"]:
#             self.data["chat_ids"].append(chat_id)

#         # Initialize user's plant data if not exists
#         user_key = self.get_user_key(user_id)
#         if user_key not in self.data["plants"]:
#             self.data["plants"][user_key] = {
#                 "username": username,
#                 "plant_name": f"{username}'s Plant",
#                 "last_watered": None,
#                 "watered_by": None,
#             }

#         self.save_data()

#         if chat_type == "group" or chat_type == "supergroup":
#             welcome_message = f"""
# 🌱 Welcome {username}! Plant Bot activated for this group! 🌱

# Your plant: **{self.data["plants"][user_key]["plant_name"]}**

# Commands:
# • /watered - Mark YOUR plant as watered
# • /status - Check everyone's plant status
# • /mystatus - Check only your plant status
# • /setplant [name] - Name your plant
# • /allplants - See everyone's plants
# • /help - Show help
# • /enable - Enable reminders
# • /disable - Disable reminders

# Everyone can track their own plants! 🌿
#             """
#         else:
#             welcome_message = f"""
# 🌱 Welcome {username}! Your personal Plant Bot! 🌱

# Your plant: **{self.data["plants"][user_key]["plant_name"]}**

# Commands:
# /watered - Mark your plant as watered
# /status - Check your plant status
# /setplant [name] - Name your plant
# /help - Show help
# /enable - Enable reminders
# /disable - Disable reminders
#             """
#         await update.message.reply_text(welcome_message)

#     async def set_plant_name(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
#         """Set a custom name for user's plant"""
#         user_id = update.effective_user.id
#         user_key = self.get_user_key(user_id)
#         username = (
#             update.effective_user.first_name
#             or update.effective_user.username
#             or "Unknown"
#         )

#         # Initialize user if not exists
#         if user_key not in self.data["plants"]:
#             self.data["plants"][user_key] = {
#                 "username": username,
#                 "plant_name": f"{username}'s Plant",
#                 "last_watered": None,
#                 "watered_by": None,
#             }

#         # Get plant name from command arguments
#         if context.args:
#             plant_name = " ".join(context.args)
#             self.data["plants"][user_key]["plant_name"] = plant_name
#             self.save_data()
#             await update.message.reply_text(
#                 f"🌱 Your plant is now named: **{plant_name}**"
#             )
#         else:
#             current_name = self.data["plants"][user_key]["plant_name"]
#             await update.message.reply_text(
#                 f"🌱 Current plant name: **{current_name}**\n\nTo change it, use: `/setplant New Plant Name`"
#             )

#     async def watered(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
#         """Mark user's plant as watered"""
#         user_id = update.effective_user.id
#         user_key = self.get_user_key(user_id)
#         username = (
#             update.effective_user.first_name
#             or update.effective_user.username
#             or "Someone"
#         )
#         chat_type = update.effective_chat.type

#         # Initialize user if not exists
#         if user_key not in self.data["plants"]:
#             self.data["plants"][user_key] = {
#                 "username": username,
#                 "plant_name": f"{username}'s Plant",
#                 "last_watered": None,
#                 "watered_by": None,
#             }

#         # Update watering data
#         self.data["plants"][user_key]["last_watered"] = datetime.now().isoformat()
#         self.data["plants"][user_key]["watered_by"] = username
#         self.save_data()

#         plant_name = self.data["plants"][user_key]["plant_name"]

#         if chat_type == "group" or chat_type == "supergroup":
#             message = f"✅ {username} watered **{plant_name}**! 🌱\n"
#             message += f"📅 {datetime.now().strftime('%Y-%m-%d')}\n"
#             message += "🗓️ Next watering in 3 days"
#         else:
#             message = f"✅ You watered **{plant_name}**! 🌱\n"
#             message += f"📅 {datetime.now().strftime('%Y-%m-%d')}\n"
#             message += "🗓️ Next watering in 3 days"

#         await update.message.reply_text(message)

#     async def my_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
#         """Check only the current user's plant status"""
#         user_id = update.effective_user.id
#         user_key = self.get_user_key(user_id)
#         username = (
#             update.effective_user.first_name or update.effective_user.username or "You"
#         )

#         if user_key not in self.data["plants"]:
#             await update.message.reply_text(
#                 "🌱 You haven't registered yet! Use /start first."
#             )
#             return

#         plant_data = self.data["plants"][user_key]
#         plant_name = plant_data["plant_name"]

#         if not plant_data["last_watered"]:
#             await update.message.reply_text(
#                 f"🌱 **{plant_name}** has never been watered (or data was reset)"
#             )
#             return

#         last_watered = datetime.fromisoformat(plant_data["last_watered"])
#         days_since = (datetime.now() - last_watered).days
#         next_watering = last_watered + timedelta(days=3)

#         status_message = f"📊 **{plant_name}** Status:\n\n"
#         status_message += (
#             f"💧 Last watered: {last_watered.strftime('%Y-%m-%d')}\n"
#         )
#         status_message += f"👤 Watered by: {plant_data['watered_by']}\n"
#         status_message += f"⏰ Days since watered: {days_since}\n"
#         status_message += f"📅 Next watering: {next_watering.strftime('%Y-%m-%d')}\n"

#         if days_since >= 3:
#             status_message += "⚠️ **Needs watering!**"
#         else:
#             days_left = 3 - days_since
#             status_message += f"✅ Good for {days_left} more day(s)"

#         await update.message.reply_text(status_message)

#     async def status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
#         """Check all plants status in the chat"""
#         if not self.data["plants"]:
#             await update.message.reply_text(
#                 "🌱 No plants registered yet! Everyone should use /start first."
#             )
#             return

#         status_message = "🌿 **All Plants Status:**\n\n"

#         for user_key, plant_data in self.data["plants"].items():
#             plant_name = plant_data["plant_name"]
#             username = plant_data["username"]

#             if not plant_data["last_watered"]:
#                 status_message += f"🌱 **{plant_name}** ({username})\n"
#                 status_message += "   ❓ Never watered\n\n"
#                 continue

#             last_watered = datetime.fromisoformat(plant_data["last_watered"])
#             days_since = (datetime.now() - last_watered).days

#             status_message += f"🌱 **{plant_name}** ({username})\n"
#             status_message += f"   💧 Last: {last_watered.strftime('%m-%d %H:%M')}\n"
#             status_message += f"   ⏰ {days_since} days ago\n"

#             if days_since >= 3:
#                 status_message += "   ⚠️ **Needs water!**\n\n"
#             else:
#                 days_left = 3 - days_since
#                 status_message += f"   ✅ Good for {days_left} day(s)\n\n"

#         await update.message.reply_text(status_message)

#     async def all_plants(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
#         """Show all registered plants"""
#         if not self.data["plants"]:
#             await update.message.reply_text("🌱 No plants registered yet!")
#             return

#         message = "🌿 **Registered Plants:**\n\n"

#         for user_key, plant_data in self.data["plants"].items():
#             plant_name = plant_data["plant_name"]
#             username = plant_data["username"]
#             message += f"🌱 **{plant_name}** - owned by {username}\n"

#         await update.message.reply_text(message)

#     async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
#         """Show help message"""
#         chat_type = update.effective_chat.type

#         if chat_type == "group" or chat_type == "supergroup":
#             help_text = """
# 🌱 **Plant Bot Commands:**

# **Plant Care:**
# • /watered - Mark YOUR plant as watered ✅
# • /mystatus - Check your plant status 📊
# • /status - Check everyone's plants 🌿
# • /allplants - List all registered plants 📝

# **Setup:**
# • /start - Register yourself and your plant 🚀
# • /setplant [name] - Give your plant a name 🏷️

# **Settings:**
# • /enable - Turn on reminders 🔔
# • /disable - Turn off reminders 🔕
# • /help - Show this help 💡

# Each person tracks their own plant! The bot won't interrupt your regular chat. 💬
#             """
#         else:
#             help_text = """
# 🌱 **Personal Plant Bot Commands:**

# • /start - Register for notifications
# • /watered - Mark your plant as watered
# • /mystatus - Check your plant status
# • /setplant [name] - Name your plant
# • /enable - Enable reminders
# • /disable - Disable reminders
# • /help - Show this help

# Perfect for tracking your personal plant care! 🌿
#             """
#         await update.message.reply_text(help_text)

#     async def enable_reminders(
#         self, update: Update, context: ContextTypes.DEFAULT_TYPE
#     ):
#         """Enable watering reminders"""
#         self.data["reminders_enabled"] = True
#         self.save_data()
#         await update.message.reply_text("✅ Watering reminders enabled for everyone!")

#     async def disable_reminders(
#         self, update: Update, context: ContextTypes.DEFAULT_TYPE
#     ):
#         """Disable watering reminders"""
#         self.data["reminders_enabled"] = False
#         self.save_data()
#         await update.message.reply_text("❌ Watering reminders disabled!")

#     async def send_reminder_notifications(self):
#         """Send reminder notifications to all registered chats"""
#         if not self.data["reminders_enabled"] or not self.data["chat_ids"]:
#             return

#         plants_needing_water = []

#         for user_key, plant_data in self.data["plants"].items():
#             plant_name = plant_data["plant_name"]
#             username = plant_data["username"]

#             if not plant_data["last_watered"]:
#                 plants_needing_water.append(
#                     f"🌱 **{plant_name}** ({username}) - Never watered!"
#                 )
#             else:
#                 last_watered = datetime.fromisoformat(plant_data["last_watered"])
#                 days_since = (datetime.now() - last_watered).days

#                 if days_since >= 3:
#                     days_overdue = days_since - 3
#                     if days_overdue == 0:
#                         plants_needing_water.append(
#                             f"🌱 **{plant_name}** ({username}) - Due today!"
#                         )
#                     else:
#                         plants_needing_water.append(
#                             f"🌱 **{plant_name}** ({username}) - {days_overdue} days overdue!"
#                         )

#         if not plants_needing_water:
#             return  # No plants need watering

#         message = "💧 **Plant Watering Reminder!**\n\n"
#         message += "\n".join(plants_needing_water)
#         message += "\n\nUse /watered when you've watered your plant! 🌿"

#         # Send to all registered chats
#         for chat_id in self.data["chat_ids"]:
#             try:
#                 await self.application.bot.send_message(chat_id=chat_id, text=message)
#             except Exception as e:
#                 logger.error(f"Failed to send reminder to {chat_id}: {e}")

#     def check_reminders(self):
#         """Check if reminders should be sent (runs in background)"""
#         if not self.data["reminders_enabled"] or not self.data["chat_ids"]:
#             return

#         # Check if any plant needs watering
#         needs_reminder = False
#         for user_key, plant_data in self.data["plants"].items():
#             if not plant_data["last_watered"]:
#                 needs_reminder = True
#                 break
#             else:
#                 last_watered = datetime.fromisoformat(plant_data["last_watered"])
#                 days_since = (datetime.now() - last_watered).days
#                 if days_since >= 3:
#                     needs_reminder = True
#                     break

#         if needs_reminder and self.application:
#             # Schedule the async function to run
#             asyncio.create_task(self.send_reminder_notifications())

#     def run_scheduler(self):
#         """Run the scheduler in a separate thread"""
#         schedule.every(12).hours.do(self.check_reminders)  # Check twice daily

#         while True:
#             schedule.run_pending()
#             time.sleep(3600)  # Sleep for 1 hour

#     def run_web_server(self):
#         """Run a simple web server for Render Web Service"""
#         app = Flask(__name__)

#         @app.route("/")
#         def home():
#             return "🌱 Plant Watering Bot is running! 🌱"

#         @app.route("/health")
#         def health():
#             return {"status": "healthy", "plants": len(self.data["plants"])}

#         port = int(os.environ.get("PORT", 10000))
#         app.run(host="0.0.0.0", port=port)

#     def run(self):
#         """Run the bot"""
#         # Create application
#         self.application = Application.builder().token(BOT_TOKEN).build()

#         # Add handlers
#         self.application.add_handler(CommandHandler("start", self.start))
#         self.application.add_handler(CommandHandler("watered", self.watered))
#         self.application.add_handler(CommandHandler("status", self.status))
#         self.application.add_handler(CommandHandler("mystatus", self.my_status))
#         self.application.add_handler(CommandHandler("setplant", self.set_plant_name))
#         self.application.add_handler(CommandHandler("allplants", self.all_plants))
#         self.application.add_handler(CommandHandler("help", self.help_command))
#         self.application.add_handler(CommandHandler("enable", self.enable_reminders))
#         self.application.add_handler(CommandHandler("disable", self.disable_reminders))

#         # Start scheduler in background thread
#         scheduler_thread = Thread(target=self.run_scheduler, daemon=True)
#         scheduler_thread.start()

#         # Start web server in background thread (for Render Web Service)
#         web_thread = Thread(target=self.run_web_server, daemon=True)
#         web_thread.start()

#         print("🌱 Multi-Plant Watering Bot is starting...")
#         print("🌐 Web server starting for Render deployment...")
#         print("Press Ctrl+C to stop the bot")

#         # Run the bot
#         self.application.run_polling()


# if __name__ == "__main__":
#     bot = PlantWateringBot()
#     bot.run()
